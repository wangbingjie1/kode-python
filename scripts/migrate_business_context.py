#!/usr/bin/env python3
"""
为已有的 business_context.json 补充 excluded_tables 和 excluded_prefixes 字段。

用法：
    python scripts/migrate_business_context.py yanfa
    python scripts/migrate_business_context.py  # 处理所有连接
"""

import json
import re
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from kode.core.model_manager import ModelManager
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger
from langchain_core.messages import HumanMessage

logger = setup_logger(__name__)


def analyze_excluded_tables(connection_name: str, questions: list, answers: dict) -> tuple:
    """
    调用 AI 分析问答，识别需要排除的表和前缀。

    复制自 BusinessUnderstanding._analyze_excluded_tables() 的逻辑。
    """
    # 加载表名列表
    schema_file = Path("schema_store") / connection_name / "schema_latest.json"
    if not schema_file.exists():
        logger.warning(f"Schema 缓存不存在: {schema_file}")
        return [], {}, []

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    if "schema" in schema_data:
        tables_dict = schema_data["schema"].get("tables", {})
    else:
        tables_dict = schema_data.get("tables", {})

    table_names = list(tables_dict.keys())

    # 构建问答文本
    qa_text = "\n".join([
        f"Q: {q[1]}\nA: {answers.get(q[0], '（未回答）')}"
        for q in questions
    ])

    prompt = f"""分析以下业务问答，识别需要排除的数据库表和表前缀。

## 数据库表名列表（共 {len(table_names)} 个）
{', '.join(table_names)}

## 业务问答
{qa_text}

## 任务
根据用户的回答，识别：
1. 哪些表应该被排除（不纳入业务分析）
2. 哪些表前缀代表已下线/废弃的模块（这些前缀的表将被排除，后续不会为这些前缀创建独立的业务域）

排除条件：
1. 用户明确说某些表/功能已下线、废弃、不再使用
2. 用户说某个前缀的表是独立系统且不需要分析
3. 用户提到某些表是测试、临时、备份用途
4. 用户说某些模块不是核心业务

## 返回格式（严格JSON）
{{
    "excluded_tables": ["table1", "table2"],
    "excluded_prefixes": ["ao_", "candy_chat_", "crush_chat_"],
    "reasons": {{
        "ao_*": "用户说 AO 开头是已下线游戏功能",
        "candy_chat_*": "用户说聊天功能已下线"
    }}
}}

重要说明：
- excluded_prefixes 应该是小写的表前缀（如 "ao_" 而非 "AO_*"）
- 用户提到的前缀都应该记录到 excluded_prefixes
- reasons 的 key 使用 "前缀_*" 格式（如 "ao_*"）

如果没有需要排除的表，返回：
{{"excluded_tables": [], "excluded_prefixes": [], "reasons": {{}}}}

只返回 JSON，不要其他内容。"""

    try:
        config_manager = ConfigManager()
        config = config_manager.get_all()
        model_manager = ModelManager(config)
        model = model_manager.get_model("quick")

        response = model.invoke([HumanMessage(content=prompt)])
        content = response.content

        # 提取 JSON
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            logger.warning("AI 分析排除表失败，返回格式错误")
            return [], {}, []

        result = json.loads(json_match.group())

        excluded_tables = result.get("excluded_tables", [])
        reasons = result.get("reasons", {})
        excluded_prefixes = result.get("excluded_prefixes", [])

        # 确保前缀是小写的
        excluded_prefixes = [p.lower() for p in excluded_prefixes]

        # 根据前缀展开为具体表名
        if excluded_prefixes:
            for prefix in excluded_prefixes:
                pattern_key = f"{prefix}*"
                for table in table_names:
                    if table.lower().startswith(prefix) and table not in excluded_tables:
                        excluded_tables.append(table)
                        if table not in reasons:
                            reasons[table] = reasons.get(pattern_key, f"匹配前缀 {prefix}")

        logger.info(f"AI 分析完成，排除 {len(excluded_tables)} 个表，排除前缀: {excluded_prefixes}")
        return excluded_tables, reasons, excluded_prefixes

    except Exception as e:
        logger.error(f"AI 分析排除表失败: {e}")
        return [], {}, []


def migrate_connection(connection_name: str) -> bool:
    """为指定连接的 business_context.json 补充 excluded_tables 字段"""

    # 1. 读取 interaction_state 中的问答数据
    state_file = Path("interaction_state") / f"BusinessUnderstanding_{connection_name}.json"
    if not state_file.exists():
        logger.warning(f"未找到问答状态文件: {state_file}")
        return False

    with open(state_file, "r", encoding="utf-8") as f:
        state_data = json.load(f)

    questions = state_data.get("questions", [])
    answers = state_data.get("answers", {})

    if not questions or not answers:
        logger.warning(f"问答数据不完整: {connection_name}")
        return False

    # 2. 调用 AI 分析
    logger.info(f"正在分析 {connection_name} 的业务问答...")
    excluded_tables, exclusion_reasons, excluded_prefixes = analyze_excluded_tables(
        connection_name, questions, answers
    )

    # 3. 更新 business_context.json
    context_file = Path("ontology_store") / connection_name / "business_context.json"
    if not context_file.exists():
        logger.warning(f"未找到 business_context.json: {context_file}")
        return False

    with open(context_file, "r", encoding="utf-8") as f:
        context_data = json.load(f)

    # 更新字段
    context_data["excluded_tables"] = excluded_tables
    context_data["exclusion_reasons"] = exclusion_reasons
    context_data["excluded_prefixes"] = excluded_prefixes

    # 保存
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(context_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 已更新 {context_file}")
    logger.info(f"   - 排除表数量: {len(excluded_tables)}")
    logger.info(f"   - 排除前缀: {excluded_prefixes}")

    return True


def main():
    if len(sys.argv) > 1:
        # 处理指定的连接
        connection_name = sys.argv[1]
        migrate_connection(connection_name)
    else:
        # 处理所有连接
        ontology_store = Path("ontology_store")
        if not ontology_store.exists():
            logger.error("ontology_store 目录不存在")
            return

        for conn_dir in ontology_store.iterdir():
            if conn_dir.is_dir():
                connection_name = conn_dir.name
                logger.info(f"处理连接: {connection_name}")
                migrate_connection(connection_name)


if __name__ == "__main__":
    main()
