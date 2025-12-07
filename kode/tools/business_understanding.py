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

        # 构建表结构描述
        tables_desc = []
        for table in table_summary.get("tables", []):
            desc = f"- **{table['name']}**"
            if table.get("comment"):
                desc += f" ({table['comment']})"

            # 添加样例数据摘要
            sample_rows = table.get("sample_rows", [])
            if sample_rows:
                # 获取字段列表
                fields = list(sample_rows[0].keys()) if sample_rows else []
                desc += f"\n  字段: {', '.join(fields[:10])}"  # 最多显示10个字段
                desc += f"\n  样例数据: {len(sample_rows)} 行"

            tables_desc.append(desc)

        tables_text = "\n".join(tables_desc)

        prompt = f"""你是一个业务分析师，正在理解一个新的数据库系统。

以下是数据库中的表结构和样例数据摘要：
{tables_text}
你的任务是：
根据 Schema 自动“推测”企业业务结构与使用动机，并提出一系列封闭式、可判断或可选择的问题，让用户确认或纠正这些推测，从而消除业务层面的歧义。
你必须遵守以下原则
- 问题必须是业务层的，不允许涉及字段级解释。
- 问题必须基于 Schema 的观察生成，而不是开放式提问。
- 每个问题必须带有明确的推测，并要求用户“确认/否认/选择”。
- 问题数量 3–5 个即可，越少越好，但必须覆盖关键业务消歧点。
- 目标是让你 100% 理解用户的主业务模式和核心分析诉求，为构建本体提供顶层业务框架。
你应优先提出以下三类问题（按需组合）：
1. 业务唯一性推测（当 Schema 出现多个可能业务）
示例逻辑（需动态生成类似问题）：
- "数据中同时包含 {{订单}}、{{广告}}、{{订阅}} 相关结构。我推测您的核心业务可能主要是 {{订单}} 驱动，请确认是：
 A. 订单业务为主
 B. 广告业务为主
 C. 订阅业务为主
 D. 多业务并存（请指明主业务）”
2. 核心商业模式推测
根据 Schema 观察收入/交易/广告/订阅等线索：
- "我在 Schema 中看到 {{交易金额}} 和 {{用户行为事件}}，推测您的商业模式更接近：
 A. 交易型（电商/平台）
 B. 订阅型（SaaS/会员）
 C. 广告/流量变现
 D. 不确定，请您指定
 是否正确？”
3. 推测用户使用动机/核心需求
根据数据中 KPI/事件/订单/用户行为等判断：
- “根据您提供的数据，我推测您最希望通过本体解决的问题是：
 A. 对关键指标（如收入、GMV、留存）进行监控
 B. 做日常数据查询（like SQL→自然语言）
 C. 获取 business insights（业务洞察）
 D. 构建完整业务知识结构
 请问推测是否正确？可多选。”

返回 JSON 格式（严格遵守）：
{{
    "questions": [
        {{"key": "q1_business_type", "question": "问题内容", "hint": "回答提示"}},
        ...
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
        self._save_complete_business_context(connection_name, questions, answers)

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

        # 保存到 ontology_store
        context_data = {
            # 🔑 主要字段：纯文本问答，直接嵌入提示词
            "qa_text": qa_text,
            # 结构化数据（备用）
            "qa_pairs": [{"question": q[1], "answer": answers.get(q[0], "")} for q in questions],
            "completed": True,
            "question_count": len(questions),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        context_file = self.storage.base_path / connection_name / "business_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)

        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[BusinessUnderstanding] 保存完整业务上下文: {context_file}")

    def get_answers(self, connection_name: str) -> Optional[Dict[str, str]]:
        """获取已保存的业务理解答案"""
        context = self.storage.load_business_context(connection_name)
        if context:
            return context.get("answers")
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
