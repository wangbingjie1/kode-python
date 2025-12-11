"""
业务理解工具

基于数据库 Schema 动态生成业务问题，作为语义层数据建模的第一阶段。
使用 InteractiveTool 基类实现多轮交互。

🔑 关键机制：
- 抛出 UserInputRequired 异常来触发前端弹窗
- 用户响应后自动保存答案并继续下一个问题
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Type, Dict, Any, List, Tuple

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from kode.tools.base import InteractiveTool
from kode.utils.ontology_storage import OntologyStorageV2
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class BusinessUnderstandingInput(BaseModel):
    """业务理解工具输入参数"""

    connection_name: str = Field(description="数据库连接名称（用于关联业务上下文和本体）")
    answer: Optional[str] = Field(
        default=None, description="用户对当前问题的回答（首次调用时为空，后续调用传入答案）"
    )
    skip_question: bool = Field(
        default=False, description="是否跳过当前问题（用户不知道答案时可跳过，但会记录）"
    )
    regenerate: bool = Field(default=False, description="是否强制重新生成问题（忽略已有状态）")


class BusinessUnderstandingTool(InteractiveTool):
    """
    业务理解工具（动态问题生成版）

    根据数据库 Schema（表名+样例数据）自动生成 5-10 个针对性业务问题。

    使用方式：
    1. 首次调用：传入 connection_name，自动读取 Schema 缓存并生成问题
    2. 后续调用：传入 connection_name 和 answer（上一个问题的答案）
    3. 完成后：自动保存到 ontology_store/{connection_name}/business_context.json
    """

    name: str = "BusinessUnderstanding"
    description: str = """
用于收集业务理解问题。系统会根据数据库结构自动生成 5-10 个针对性问题。

使用场景：
- 首次连接新数据库时
- 需要重新理解业务时

输入参数：
- connection_name: 数据库连接名（必须已有 Schema 缓存）
- answer: 对当前问题的回答（首次调用时不传）
- skip_question: 跳过当前问题
- regenerate: 强制重新生成问题

流程：
1. 首次调用：读取 Schema 缓存，AI 生成问题列表
2. 后续调用：传入 answer 回答问题
3. 完成后：保存到 ontology_store/{connection_name}/business_context.json

前置条件：必须先运行 DatabaseSchemaExtractor 提取 Schema。
"""
    args_schema: Type[BaseModel] = BusinessUnderstandingInput

    # Pydantic 字段声明
    storage: OntologyStorageV2 = Field(default_factory=OntologyStorageV2, exclude=True)
    schema_store_path: Path = Field(default=Path("schema_store"), exclude=True)

    # 🔑 异步响应支持（用于 UserInputRequired 机制）
    _user_response_event: Optional[asyncio.Event] = None
    _user_response_data: Optional[Dict[str, Any]] = None
    _current_connection_name: Optional[str] = None  # 保存当前处理的 connection_name
    _current_question_key: Optional[str] = None  # 保存当前问题的 key

    class Config:
        """Pydantic config to allow arbitrary types."""

        arbitrary_types_allowed = True

    def _load_table_summary_from_cache(self, connection_name: str) -> Optional[Dict[str, Any]]:
        """
        从 schema_store 读取已缓存的 Schema，提取表名和样例数据

        Args:
            connection_name: 数据库连接名

        Returns:
            表结构摘要，格式：{"tables": [{"name": "...", "comment": "...", "sample_rows": [...]}]}
            如果缓存不存在，返回 None
        """
        schema_file = self.schema_store_path / connection_name / "schema_latest.json"

        if not schema_file.exists():
            logger.warning(f"Schema 缓存不存在: {schema_file}")
            return None

        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            # 兼容两种格式：schema.tables 或直接 tables
            if "schema" in schema_data:
                tables_dict = schema_data["schema"].get("tables", {})
            else:
                tables_dict = schema_data.get("tables", {})

            if not tables_dict:
                logger.warning(f"Schema 中没有表: {connection_name}")
                return None

            # 提取表名、注释和样例数据
            tables = []
            for table_name, table_info in tables_dict.items():
                table_summary = {
                    "name": table_name,
                    "comment": table_info.get("comment", ""),
                }

                # 提取样例数据（如果有）
                sample_data = table_info.get("sample_data", {})
                if sample_data and "rows" in sample_data:
                    table_summary["sample_rows"] = sample_data["rows"][:5]  # 最多5行
                else:
                    table_summary["sample_rows"] = []

                tables.append(table_summary)

            logger.info(f"从缓存加载了 {len(tables)} 个表的摘要: {connection_name}")
            return {"tables": tables, "connection_name": connection_name}

        except Exception as e:
            logger.error(f"读取 Schema 缓存失败: {e}")
            return None

    def _generate_questions(self, table_summary: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        调用 LLM 根据表结构生成 5-10 个业务问题

        Args:
            table_summary: 表结构摘要

        Returns:
            问题列表：[(key, question_text, hint), ...]
        """
        from kode.core.model_manager import ModelManager
        from kode.utils.config import ConfigManager

        # 构建表结构描述（包含实际样例数据）
        tables_desc = []
        for table in table_summary.get("tables", []):
            desc = f"### {table['name']}"
            if table.get("comment"):
                desc += f" ({table['comment']})"
            desc += "\n"

            # 添加样例数据（实际内容，不只是行数）
            sample_rows = table.get("sample_rows", [])
            if sample_rows:
                # 获取字段列表
                fields = list(sample_rows[0].keys()) if sample_rows else []
                desc += f"字段: {', '.join(fields[:15])}\n"  # 最多显示15个字段

                # 🔑 显示实际样例数据（最多3行，每行截断）
                desc += "样例数据:\n"
                for i, row in enumerate(sample_rows[:3]):
                    # 格式化行数据，每个值截断到50字符
                    row_items = []
                    for k, v in list(row.items())[:8]:  # 最多8个字段
                        v_str = str(v) if v is not None else "NULL"
                        if len(v_str) > 50:
                            v_str = v_str[:50] + "..."
                        row_items.append(f"{k}={v_str}")
                    desc += f"  {i+1}. {' | '.join(row_items)}\n"
            else:
                desc += "(无样例数据)\n"

            tables_desc.append(desc)

        tables_text = "\n".join(tables_desc)

        # 生成表名列表（用于冗余表问题）
        table_names = [t["name"] for t in table_summary.get("tables", [])]
        table_count = len(table_names)

        prompt = f"""你是一个业务分析师，正在理解一个新的数据库系统。

## 数据库概览
- 表数量: {table_count}
- 表名列表: {', '.join(table_names[:50])}{"..." if table_count > 50 else ""}

## 表结构和样例数据
{tables_text}

## 你的任务
根据 Schema 自动"推测"企业业务结构与使用动机，并提出封闭式问题让用户确认或纠正。

## 原则
- 问题必须是业务层的，不涉及字段级解释
- 每个问题必须带有明确的推测，要求用户"确认/否认/选择"
- 问题数量 10个以内，越少越好，但必须覆盖关键业务消歧点。
- 目标是让你 100% 理解用户的主业务模式和核心分析诉求，为构建本体提供顶层业务框架。
- **重点关注可能存在的独立子系统、已下线功能、废弃模块**（用户的回答可帮助识别无需分析的表）
- **问题必须包含以下类别：1 产品名称确认 2 产品定位推测（提供什么服务或者解决什么需求）3 业务唯一性推测 4  商业模式推测 5 获客模式推测  6 使用目的和关注的关键指标

## 以下是问题示例，仅供参考，切勿照抄，你需要根据以上的问题类别设计若干问题完成理解整个业务的终极目标

1. **产品/系统识别**
"我看到表名中有 {{AO_xxx}}、{{main_xxx}}、{{legacy_xxx}} 等前缀，推测：
 A. AO 开头是独立子系统（请说明是否在用）
 B. legacy 开头是历史遗留（已下线？）
 C. 都是同一系统的不同模块
 D. 请您说明"

2. **业务范围推测**
"数据中同时包含 {{订单}}、{{广告}}、{{日志}} 相关结构。推测：
 A. 订单是核心业务，广告/日志是辅助
 B. 多业务并存
 C. 部分是已下线或废弃功能（请指明）"

3. **商业模式推测**
"我看到 {{交易金额}} 和 {{用户行为}}，推测商业模式是：
 A. 交易型（电商/平台）
 B. 订阅型（SaaS/会员）
 C. 广告变现
 D. 其他（请说明）"

4. **分析需求**
"您最希望解决的问题是：
 A. 关键指标监控（收入、GMV、留存）
 B. 日常数据查询
 C. 业务洞察分析
 D. 其他"

## 返回格式（严格JSON）
{{
    "questions": [
        {{"key": "q1_xxx", "question": "问题内容", "hint": "回答提示"}}
    ]
}}

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
                logger.error(f"LLM 返回格式错误: {content[:200]}")
                return self._get_fallback_questions()

            result = json.loads(json_match.group())
            questions = result.get("questions", [])

            if not questions:
                logger.warning("LLM 没有生成问题，使用默认问题")
                return self._get_fallback_questions()

            # 转换格式
            return [(q["key"], q["question"], q.get("hint", "请详细描述")) for q in questions]

        except Exception as e:
            logger.error(f"生成问题失败: {e}")
            return self._get_fallback_questions()

    def _get_fallback_questions(self) -> List[Tuple[str, str, str]]:
        """获取默认问题（当 LLM 生成失败时使用）"""
        return [
            ("business_type", "这个系统的核心业务是什么？", "请描述主营业务，如：电商、ERP、CRM等"),
            ("business_model", "商业模式是什么？", "如：B2B、B2C、订阅制、平台交易等"),
            ("key_process", "关键业务流程是什么？", "如：下单→支付→发货→收货"),
            ("key_metrics", "最关注哪些业务指标？", "如：GMV、订单量、转化率、复购率等"),
            ("user_goal", "你希望解决什么问题？", "如：分析销售趋势、优化库存、提升转化等"),
        ]

    def _run_interactive(
        self,
        session_id: str,
        connection_name: str,
        answer: Optional[str] = None,
        skip_question: bool = False,
        regenerate: bool = False,
        **kwargs,
    ) -> str:
        """
        执行业务理解交互

        Args:
            session_id: 会话ID（使用 connection_name）
            connection_name: 数据库连接名
            answer: 用户答案
            skip_question: 是否跳过
            regenerate: 是否重新生成问题

        Returns:
            下一个问题或完成消息
        """
        session_id = connection_name

        # 加载已有状态
        state = self._load_state(session_id)

        # 首次调用或强制重新生成
        if state is None or regenerate:
            # 从缓存读取表结构
            table_summary = self._load_table_summary_from_cache(connection_name)

            if table_summary is None:
                return (
                    "❌ **未找到 Schema 缓存**\n\n"
                    f'请先运行 `DatabaseSchemaExtractor(connection_name="{connection_name}")` 提取数据库结构。'
                )

            # 生成问题
            questions = self._generate_questions(table_summary)
            state = {
                "questions": questions,
                "answers": {},
                "table_count": len(table_summary.get("tables", [])),
            }
            self._save_state(session_id, state)
            logger.info(f"生成了 {len(questions)} 个业务问题: {connection_name}")

        questions = state["questions"]
        answers = state.get("answers", {})

        # 处理用户答案
        if answer is not None or skip_question:
            current_idx = len(answers)
            if current_idx < len(questions):
                q_key = questions[current_idx][0]

                if skip_question:
                    answers[q_key] = "（用户跳过）"
                else:
                    answers[q_key] = answer.strip()

                state["answers"] = answers
                self._save_state(session_id, state)

                # 同时保存到 ontology_store
                self.storage.update_business_context(connection_name, answers)

        # 检查是否完成
        if len(answers) >= len(questions):
            # 清理交互状态
            self._clear_state(session_id)
            return self._format_completion_message(connection_name, questions, answers)

        # 返回下一个问题
        return self._format_question(len(answers), questions, answers, connection_name)

    def _format_question(
        self,
        question_index: int,
        questions: List[Tuple[str, str, str]],
        existing_answers: Dict[str, str],
        connection_name: str,
    ) -> str:
        """
        格式化问题，抛出 UserInputRequired 异常以触发前端弹窗

        这个方法会抛出异常而不是返回字符串！
        异常被 anthropic_streaming.py 捕获后，会发送 SSE 事件给前端。
        """
        from kode.exceptions import UserInputRequired

        if question_index >= len(questions):
            return json.dumps(
                {"status": "completed", "message": "所有问题已回答完毕。"}, ensure_ascii=False
            )

        key, question_text, hint = questions[question_index]

        # 🔑 保存当前状态，以便在 _set_user_response 中使用
        self._current_connection_name = connection_name
        self._current_question_key = key

        # 🔑 创建 asyncio.Event 用于等待用户响应
        self._user_response_event = asyncio.Event()
        self._user_response_data = None

        # 构建简洁的上下文（不显示已回答的问题，避免冗余）
        context_parts = [f"📋 业务理解问卷 ({question_index + 1}/{len(questions)})"]
        context_parts.append(f"💡 提示: {hint}")
        context_parts.append(f"🔗 connection_name: {connection_name}")

        context = "\n".join(context_parts)

        # 🔑 抛出 UserInputRequired 异常，触发前端弹窗
        # anthropic_streaming.py 会捕获这个异常并发送 SSE 事件
        logger.info(f"[BusinessUnderstanding] 抛出 UserInputRequired: {question_text}")
        raise UserInputRequired(
            question=question_text,
            question_type="text",
            context=context,
            required=True,
            allow_defer=True,  # 允许用户跳过
            tool_instance=self,  # 传递工具实例以便接收响应
        )

    def _format_completion_message(
        self, connection_name: str, questions: List[Tuple[str, str, str]], answers: Dict[str, str]
    ) -> str:
        """格式化完成消息，并保存完整的问答数据"""

        # 🔑 保存完整的问答数据（包含问题文本，供 OntologyBuilder 使用）
        # 同时会调用 AI 分析排除表
        self._save_complete_business_context(connection_name, questions, answers)

        # 读取保存的结果（包含排除表信息）
        context_file = self.storage.base_path / connection_name / "business_context.json"
        excluded_tables = []
        exclusion_reasons = {}
        if context_file.exists():
            with open(context_file, "r", encoding="utf-8") as f:
                context_data = json.load(f)
                excluded_tables = context_data.get("excluded_tables", [])
                exclusion_reasons = context_data.get("exclusion_reasons", {})

        message_parts = []

        message_parts.append("✅ **业务理解完成！**")
        message_parts.append("")
        message_parts.append("感谢你的回答！以下是你的业务上下文：")
        message_parts.append("")

        # 汇总答案
        for i, (key, question_text, _) in enumerate(questions):
            ans = answers.get(key, "（未回答）")
            message_parts.append(f"**{i + 1}. {question_text}**")
            message_parts.append(f"   {ans}")
            message_parts.append("")

        # 🔑 显示排除表信息
        if excluded_tables:
            message_parts.append(f"🗑️ **根据你的回答，以下 {len(excluded_tables)} 个表将被排除：**")
            # 按原因分组显示
            reasons_grouped: Dict[str, List[str]] = {}
            for table in excluded_tables:
                reason = exclusion_reasons.get(table, "业务分析不需要")
                if reason not in reasons_grouped:
                    reasons_grouped[reason] = []
                reasons_grouped[reason].append(table)

            for reason, tables in reasons_grouped.items():
                if len(tables) <= 5:
                    message_parts.append(f"   - {', '.join(tables)} ({reason})")
                else:
                    message_parts.append(f"   - {', '.join(tables[:5])}... 等 {len(tables)} 个表 ({reason})")
            message_parts.append("")

        # 保存位置
        message_parts.append(f"📁 业务上下文已保存到：")
        message_parts.append(f"   `ontology_store/{connection_name}/business_context.json`")
        message_parts.append("")

        # 下一步提示
        message_parts.append("🚀 **下一步：**")
        message_parts.append("   现在可以开始构建本体了！请使用 `OntologyBuilder` 工具。")

        return "\n".join(message_parts)

    def _save_complete_business_context(
        self, connection_name: str, questions: List[Tuple[str, str, str]], answers: Dict[str, str]
    ) -> None:
        """
        保存完整的业务上下文

        🔑 核心格式：qa_text（纯文本问答，直接嵌入提示词）
        🔑 新增：用 AI 智能分析问答内容，识别需要排除的表

        Args:
            connection_name: 数据库连接名
            questions: 问题列表 [(key, question_text, hint), ...]
            answers: 答案字典 {key: answer}
        """
        from datetime import datetime

        # 🔑 构建纯文本问答（直接可嵌入提示词）
        qa_lines = []
        for i, (key, question_text, hint) in enumerate(questions, 1):
            answer = answers.get(key, "（未回答）")
            qa_lines.append(f"**Q{i}: {question_text}**")
            qa_lines.append(f"A: {answer}")
            qa_lines.append("")  # 空行分隔

        qa_text = "\n".join(qa_lines).strip()

        # 🔑 用 AI 智能分析问答，识别需要排除的表和前缀
        excluded_tables, exclusion_reasons, excluded_prefixes = self._analyze_excluded_tables(
            connection_name, questions, answers
        )

        # 🔥 新增：提取 5 个核心业务字段（用于本体 meta 信息）
        business_fields = self._extract_business_fields(questions, answers)

        # 保存到 ontology_store（统一格式）
        context_data = {
            # 兼容旧格式
            "answers": answers,
            # 结构化问答对（包含问题文本，用于构建提示词）
            "qa_pairs": [{"question": q[1], "answer": answers.get(q[0], "")} for q in questions],
            # 🔑 排除表列表和原因（供 DatabaseSchemaClusterer 使用）
            "excluded_tables": excluded_tables,
            "exclusion_reasons": exclusion_reasons,
            # 🔑 新增：排除前缀列表（供 DatabaseSchemaClusterer 和 DomainUncertaintyAnalyzer 使用）
            "excluded_prefixes": excluded_prefixes,
            # 🔥 新增：提取的核心业务字段（供 OntologyBuilder 使用）
            "product_name": business_fields.get("product_name", ""),
            "business_model": business_fields.get("business_model", ""),
            "revenue_formula": business_fields.get("revenue_formula", ""),
            "conversion_path": business_fields.get("conversion_path", ""),
            "key_metrics": business_fields.get("key_metrics", ""),
            "completed": True,
            "question_count": len(questions),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        context_file = self.storage.base_path / connection_name / "business_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"[BusinessUnderstanding] 保存完整业务上下文: {context_file}, "
            f"排除表数量: {len(excluded_tables)}, 排除前缀: {excluded_prefixes}"
        )
        if exclusion_reasons:
            # 只显示前5个原因，避免日志过长
            reasons_preview = dict(list(exclusion_reasons.items())[:5])
            logger.info(f"[BusinessUnderstanding] 排除原因（前5个）: {reasons_preview}")

    def _analyze_excluded_tables(
        self,
        connection_name: str,
        questions: List[Tuple[str, str, str]],
        answers: Dict[str, str]
    ) -> Tuple[List[str], Dict[str, str], List[str]]:
        """
        用 AI 智能分析问答内容，识别需要排除的表和前缀

        根据用户的回答（如"AO开头的表是已下线功能"），自动识别并排除相关表。

        Args:
            connection_name: 数据库连接名
            questions: 问题列表
            answers: 答案字典

        Returns:
            (excluded_tables, exclusion_reasons, excluded_prefixes)
            - excluded_tables: 需要排除的表名列表
            - exclusion_reasons: 排除原因字典 {"table_name": "原因"}
            - excluded_prefixes: 需要排除的表前缀列表（如 ["ao_", "candy_chat_"]）
        """
        from kode.core.model_manager import ModelManager
        from kode.utils.config import ConfigManager

        # 加载表名列表
        table_summary = self._load_table_summary_from_cache(connection_name)
        if not table_summary:
            return [], {}, []

        table_names = [t["name"] for t in table_summary.get("tables", [])]

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
                logger.warning(f"[BusinessUnderstanding] AI 分析排除表失败，返回格式错误")
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
                            # 使用原因，如果没有则生成默认原因
                            if table not in reasons:
                                reasons[table] = reasons.get(pattern_key, f"匹配前缀 {prefix}")

            logger.info(
                f"[BusinessUnderstanding] AI 分析完成，排除 {len(excluded_tables)} 个表，"
                f"排除前缀: {excluded_prefixes}"
            )
            return excluded_tables, reasons, excluded_prefixes

        except Exception as e:
            logger.error(f"[BusinessUnderstanding] AI 分析排除表失败: {e}")
            return [], {}, []

    def _extract_business_fields(
        self,
        questions: List[Tuple[str, str, str]],
        answers: Dict[str, str]
    ) -> Dict[str, str]:
        """
        从业务问答中提取 5 个核心业务字段（用于本体 meta 信息）

        提取字段：
        1. product_name: 产品名称（如"AI对话平台"）
        2. business_model: 商业模式（如"订阅制+按量付费"）
        3. revenue_formula: 收入公式（如"MRR = 订阅收入 + 按量消费"）
        4. conversion_path: 转化路径（如"注册 -> 免费试用 -> 订阅付费"）
        5. key_metrics: 核心指标（如"MRR, DAU, 留存率"）

        Args:
            questions: 问题列表
            answers: 答案字典

        Returns:
            包含 5 个字段的字典
        """
        from kode.core.model_manager import ModelManager
        from kode.utils.config import ConfigManager
        from langchain_core.messages import HumanMessage

        # 构建问答文本
        qa_text = "\n".join([
            f"**Q{i+1}: {q[1]}**\nA: {answers.get(q[0], '（未回答）')}\n"
            for i, q in enumerate(questions)
        ])

        prompt = f"""你是业务分析专家。请从以下业务问答中提取 5 个核心业务字段。

## 业务问答
{qa_text}

## 任务
从上述问答中提取以下 5 个字段（如果问答中没有明确信息，请根据上下文推断或留空）：

1. **product_name**（产品名称）
   - 用户的核心产品/服务名称
   - 如果有多个产品线，用斜杠分隔（如"AI对话/AI创作"）
   - 示例："AI对话平台"、"SaaS ERP系统"

2. **business_model**（商业模式）
   - 用户的盈利模式
   - 示例："订阅制（月费/年费）"、"按量付费（按token）"、"订阅+增值服务"

3. **revenue_formula**（收入公式）
   - 用户的收入计算公式
   - 示例："MRR = 订阅用户数 × 月费单价"、"收入 = 订阅费 + Token消费"
   - 如果问答中没有明确信息，基于 business_model 推断

4. **conversion_path**（转化路径）
   - 用户从获客到付费的转化漏斗
   - 示例："注册 -> 免费试用 -> 订阅付费"、"访问 -> 注册 -> 首次充值 -> 续费"

5. **key_metrics**（核心指标）
   - 用户最关注的业务指标（3-5个）
   - 示例："MRR, Churn Rate, ARPU"、"DAU, 留存率, 新增用户"

## 返回格式（严格JSON）
{{
    "product_name": "...",
    "business_model": "...",
    "revenue_formula": "...",
    "conversion_path": "...",
    "key_metrics": "..."
}}

**重要规则**：
- 每个字段必须是单行文本（不要换行）
- 如果问答中没有明确信息，**推断或留空**（不要返回"未知"）
- key_metrics 使用逗号分隔（如"MRR, DAU, Churn Rate"）
- 只返回 JSON，不要其他内容"""

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
                logger.warning(f"[BusinessUnderstanding] AI 提取业务字段失败，返回格式错误")
                return {
                    "product_name": "",
                    "business_model": "",
                    "revenue_formula": "",
                    "conversion_path": "",
                    "key_metrics": "",
                }

            result = json.loads(json_match.group())

            # 确保所有字段都存在
            business_fields = {
                "product_name": result.get("product_name", ""),
                "business_model": result.get("business_model", ""),
                "revenue_formula": result.get("revenue_formula", ""),
                "conversion_path": result.get("conversion_path", ""),
                "key_metrics": result.get("key_metrics", ""),
            }

            logger.info(
                f"[BusinessUnderstanding] 提取业务字段成功:\n"
                f"  - product_name: {business_fields['product_name']}\n"
                f"  - business_model: {business_fields['business_model']}\n"
                f"  - revenue_formula: {business_fields['revenue_formula']}\n"
                f"  - conversion_path: {business_fields['conversion_path']}\n"
                f"  - key_metrics: {business_fields['key_metrics']}"
            )
            return business_fields

        except Exception as e:
            logger.error(f"[BusinessUnderstanding] AI 提取业务字段失败: {e}")
            return {
                "product_name": "",
                "business_model": "",
                "revenue_formula": "",
                "conversion_path": "",
                "key_metrics": "",
            }

    def get_answers(self, connection_name: str) -> Optional[Dict[str, str]]:
        """
        获取已保存的业务理解答案

        返回包含核心业务字段的字典：
        - product_name: 产品名称
        - business_model: 商业模式
        - revenue_formula: 收入公式
        - conversion_path: 转化路径
        - key_metrics: 核心指标

        注意：这些字段是从原始问答中提取的结构化信息
        """
        context = self.storage.load_business_context(connection_name)
        if context:
            # 🔥 优先返回提取的核心字段（如果存在）
            business_fields = {
                "product_name": context.get("product_name", ""),
                "business_model": context.get("business_model", ""),
                "revenue_formula": context.get("revenue_formula", ""),
                "conversion_path": context.get("conversion_path", ""),
                "key_metrics": context.get("key_metrics", ""),
            }

            # 如果核心字段都为空，说明是旧版数据（还没有提取字段）
            # 此时返回原始 answers（兼容旧代码）
            if all(v == "" for v in business_fields.values()):
                return context.get("answers")

            return business_fields
        return None

    def is_completed(self, connection_name: str) -> bool:
        """检查业务理解是否完成"""
        return self.storage.is_business_context_completed(connection_name)

    def reset(self, connection_name: str) -> str:
        """重置业务理解"""
        # 清除 ontology_store 中的文件
        context_file = self.storage.base_path / connection_name / "business_context.json"
        if context_file.exists():
            context_file.unlink()

        # 清除交互状态
        self._clear_state(connection_name)

        return f"✅ 已重置 {connection_name} 的业务理解问卷，可以重新开始。"

    # ============ 🔑 异步响应支持方法（用于 UserInputRequired 机制） ============

    async def _set_user_response(self, response: Dict[str, Any]):
        """
        接收用户响应并保存到状态中

        由 anthropic_streaming.py 调用，当用户通过前端提交回答时。

        Args:
            response: 用户响应数据，格式 {"answer": "用户的回答"}
        """
        self._user_response_data = response
        if self._user_response_event:
            self._user_response_event.set()

        # 🔑 自动保存用户答案到状态
        answer = response.get("answer", "")
        if self._current_connection_name and self._current_question_key:
            state = self._load_state(self._current_connection_name)
            if state:
                state["answers"][self._current_question_key] = answer
                self._save_state(self._current_connection_name, state)
                # 同时保存到 ontology_store
                self.storage.update_business_context(
                    self._current_connection_name, state["answers"]
                )
                logger.info(
                    f"[BusinessUnderstanding] 保存答案: {self._current_question_key} = {answer[:50]}..."
                )

                # 🔑 检查是否所有问题都已回答完毕，如果是则自动触发完成逻辑
                questions = state.get("questions", [])
                answers = state.get("answers", {})
                if len(answers) >= len(questions) and len(questions) > 0:
                    logger.info(
                        f"[BusinessUnderstanding] 所有问题已回答完毕 ({len(answers)}/{len(questions)})，触发排除表分析..."
                    )
                    # 调用完成逻辑，生成 excluded_tables
                    self._save_complete_business_context(
                        self._current_connection_name, questions, answers
                    )
                    logger.info(
                        f"[BusinessUnderstanding] 排除表分析完成，business_context.json 已更新"
                    )

    async def _wait_for_response(self) -> str:
        """
        等待用户响应，并返回包含下一步指令的消息

        Returns:
            包含用户答案和下一步指令的结构化消息
        """
        if not self._user_response_event:
            raise RuntimeError("No event set up for waiting user response")

        # 等待用户响应（5 分钟超时）
        try:
            await asyncio.wait_for(self._user_response_event.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            logger.error("[BusinessUnderstanding] 用户响应超时 (5 分钟)")
            return json.dumps(
                {"status": "timeout", "message": "用户未在规定时间内回答"}, ensure_ascii=False
            )

        # 提取答案
        if not self._user_response_data:
            return json.dumps({"status": "error", "message": "无响应数据"}, ensure_ascii=False)

        answer = self._user_response_data.get("answer")
        if answer is None:
            answer = ""

        # 检查是否还有更多问题
        state = (
            self._load_state(self._current_connection_name)
            if self._current_connection_name
            else None
        )
        questions_count = len(state.get("questions", [])) if state else 0
        answers_count = len(state.get("answers", {})) if state else 0
        has_more_questions = answers_count < questions_count

        # 🔑 返回结构化消息，包含下一步指令
        result = {
            "status": "answer_received",
            "answer": str(answer),
            "question_key": self._current_question_key,
            "connection_name": self._current_connection_name,
            "progress": f"{answers_count}/{questions_count}",
            "has_more_questions": has_more_questions,
        }

        if has_more_questions:
            result["next_action"] = (
                f'继续调用 BusinessUnderstanding(connection_name="{self._current_connection_name}") 获取下一个问题'
            )
        else:
            result["next_action"] = "所有问题已回答完毕，业务理解问卷完成"

        logger.info(
            f"[BusinessUnderstanding] 用户回答: {answer[:50]}..., 进度: {answers_count}/{questions_count}"
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
