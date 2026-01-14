#!/usr/bin/env python3
"""
重新运行聚类和不确定性分析（使用已有的排除配置）

用法：
    python scripts/rerun_clustering.py yanfa
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from kode.tools.schema_clustering_tool import DatabaseSchemaClusterer
from kode.tools.domain_uncertainty_analyzer import DomainUncertaintyAnalyzer
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/rerun_clustering.py <connection_name>")
        sys.exit(1)

    connection_name = sys.argv[1]
    schema_file = f"schema_store/{connection_name}/schema_latest.json"

    if not Path(schema_file).exists():
        print(f"Schema 文件不存在: {schema_file}")
        sys.exit(1)

    # 检查排除配置
    context_file = Path(f"ontology_store/{connection_name}/business_context.json")
    if context_file.exists():
        with open(context_file, "r", encoding="utf-8") as f:
            ctx = json.load(f)
        excluded_tables = ctx.get("excluded_tables", [])
        excluded_prefixes = ctx.get("excluded_prefixes", [])
        print(f"📋 排除配置:")
        print(f"   - 排除表数量: {len(excluded_tables)}")
        print(f"   - 排除前缀: {excluded_prefixes}")
    else:
        print("⚠️ 未找到 business_context.json，将不会排除任何表")

    # 1. 重新运行聚类
    print("\n🔄 重新运行聚类...")
    clusterer = DatabaseSchemaClusterer()
    result = clusterer._run(
        connection_name=connection_name,
        schema_file=schema_file,
        target_tables_per_domain=10,
        max_columns_for_analysis=20,
        llm_model="main",
        output_language="en",
    )
    result_data = json.loads(result)

    if result_data.get("status") == "success":
        summary = result_data.get("clustering_summary", {})
        print(f"✅ 聚类完成:")
        print(f"   - 分析表数: {summary.get('analyzed_tables')}")
        print(f"   - 排除表数: {summary.get('excluded_tables')}")
        print(f"   - 域数量: {summary.get('total_domains')}")
        for d in summary.get("domains", []):
            print(f"     • {d['name']}: {d['table_count']} 表")
    else:
        print(f"❌ 聚类失败: {result_data.get('message')}")
        sys.exit(1)

    # 2. 重新运行不确定性分析
    print("\n🔄 重新运行不确定性分析...")
    analyzer = DomainUncertaintyAnalyzer()
    result = analyzer._run(
        connection_name=connection_name,
        llm_model="main",
        max_concurrent_domains=5
    )
    result_data = json.loads(result)

    if result_data.get("status") == "success":
        stats = result_data.get("statistics", {})
        print(f"✅ 不确定性分析完成:")
        print(f"   - 分析域数: {stats.get('analyzed_domains')}")
        print(f"   - 跳过域数: {stats.get('skipped_domains')}")
        print(f"   - 不确定性总数: {stats.get('total_uncertainties')}")
        print(f"   - 高优先级: {stats.get('high_priority')}")
        print(f"   - 中优先级: {stats.get('medium_priority')}")
        print(f"   - 低优先级: {stats.get('low_priority')}")
    else:
        print(f"❌ 不确定性分析失败: {result_data.get('message')}")
        sys.exit(1)

    print("\n✅ 全部完成！")


if __name__ == "__main__":
    main()
