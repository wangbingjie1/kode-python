"""
修复 api_call_traces 表中的错误数据

由于之前对 Anthropic API input_tokens 字段的理解错误，
导致数据库中保存的 regular_input_cost 和 total_cost 是错误的。

此脚本将：
1. 方案A（推荐）：删除所有旧的错误数据
2. 方案B（可选）：重新计算所有记录的成本
"""

import asyncio
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from kode.database.session import async_session_maker
from kode.models.api_trace import APICallTrace
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


async def delete_all_traces():
    """方案A：删除所有旧数据（推荐）"""
    async with async_session_maker() as db:
        try:
            # 删除所有记录
            result = await db.execute(select(APICallTrace))
            traces = result.scalars().all()
            count = len(traces)

            await db.execute(delete(APICallTrace))
            await db.commit()

            logger.info(f"✅ 已删除 {count} 条旧的 API trace 记录")
            logger.info("新的会话将使用正确的计算逻辑")
            return count

        except Exception as e:
            logger.error(f"❌ 删除失败: {e}")
            await db.rollback()
            raise


async def recalculate_all_costs():
    """方案B：重新计算所有记录的成本（可选）"""
    async with async_session_maker() as db:
        try:
            # 获取所有记录
            result = await db.execute(select(APICallTrace))
            traces = result.scalars().all()

            logger.info(f"开始重新计算 {len(traces)} 条记录...")

            updated = 0
            for trace in traces:
                # ✅ 正确计算：input_tokens 本身就是常规输入
                regular_input = trace.input_tokens
                cache_creation = trace.cache_creation_input_tokens
                cache_read = trace.cache_read_input_tokens
                output = trace.output_tokens

                # 重新计算成本
                regular_input_cost = regular_input * 3.0 / 1_000_000
                cache_creation_cost = cache_creation * 3.75 / 1_000_000
                cache_read_cost = cache_read * 0.30 / 1_000_000
                output_cost = output * 15.0 / 1_000_000

                total_cost = (
                    regular_input_cost
                    + cache_creation_cost
                    + cache_read_cost
                    + output_cost
                )

                # 计算节省（无缓存成本 - 实际成本）
                true_total_input = regular_input + cache_creation + cache_read
                no_cache_cost = true_total_input * 3.0 / 1_000_000 + output_cost
                cost_savings = no_cache_cost - total_cost

                # 更新记录
                trace.regular_input_cost = round(regular_input_cost, 8)
                trace.cache_creation_cost = round(cache_creation_cost, 8)
                trace.cache_read_cost = round(cache_read_cost, 8)
                trace.output_cost = round(output_cost, 8)
                trace.total_cost = round(total_cost, 8)
                trace.cost_savings = round(cost_savings, 8)

                db.add(trace)
                updated += 1

                if updated % 100 == 0:
                    logger.info(f"已处理 {updated}/{len(traces)} 条记录...")

            await db.commit()
            logger.info(f"✅ 成功重新计算 {updated} 条记录的成本")
            return updated

        except Exception as e:
            logger.error(f"❌ 重新计算失败: {e}")
            await db.rollback()
            raise


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("API Call Traces 数据修复工具")
    print("=" * 80)
    print("\n请选择修复方案：")
    print("1. 删除所有旧数据（推荐）")
    print("2. 重新计算所有成本（保留历史数据）")
    print("0. 退出")
    print()

    choice = input("请输入选项 (0/1/2): ").strip()

    if choice == "1":
        print("\n⚠️  警告：此操作将删除所有历史 API trace 记录！")
        confirm = input("确认删除？(yes/no): ").strip().lower()
        if confirm == "yes":
            count = await delete_all_traces()
            print(f"\n✅ 成功删除 {count} 条记录")
        else:
            print("\n❌ 已取消")

    elif choice == "2":
        print("\n开始重新计算所有成本...")
        count = await recalculate_all_costs()
        print(f"\n✅ 成功更新 {count} 条记录")

    elif choice == "0":
        print("\n退出")

    else:
        print("\n❌ 无效选项")


if __name__ == "__main__":
    asyncio.run(main())
