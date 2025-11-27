"""
业务理解工具

实现产品经理要求的「业务理解五问」，作为语义层数据建模的第一阶段。
使用 InteractiveTool 基类实现多轮交互。
"""

from typing import Optional, Type, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from kode.tools.base import InteractiveTool
from kode.utils.ontology_storage import OntologyStorageV2


class BusinessUnderstandingInput(BaseModel):
    """业务理解工具输入参数"""

    connection_name: str = Field(
        description="数据库连接名称（用于关联业务上下文和本体）"
    )
    answer: Optional[str] = Field(
        default=None,
        description="用户对当前问题的回答（首次调用时为空，后续调用传入答案）"
    )
    skip_question: bool = Field(
        default=False,
        description="是否跳过当前问题（用户不知道答案时可跳过，但会记录）"
    )


class BusinessUnderstandingTool(InteractiveTool):
    """
    业务理解五问工具

    按顺序向用户提问以下5个核心业务问题：
    1. 你的产品是什么？
    2. 你的商业模式是什么？
    3. 你的收入公式是什么？
    4. 你的转化路径是什么？
    5. 你最关心的3-5个指标是什么？

    使用方式：
    1. 首次调用：传入 connection_name（不传 answer）
    2. 后续调用：传入 connection_name 和 answer（上一个问题的答案）
    3. 完成后：自动保存到 ontology_store/{connection_name}/business_context.json
    """

    name: str = "BusinessUnderstanding"
    description: str = """
用于收集业务理解的五个核心问题。这是语义层数据建模的第一步，必须在构建本体之前完成。

使用场景：
- 首次连接新数据库时
- 需要重新理解业务时

输入参数：
- connection_name: 数据库连接名
- answer: 对当前问题的回答（首次调用时不传）
- skip_question: 是否跳过当前问题（默认False）

返回：
- 下一个问题（未完成时）
- 完成消息和答案汇总（完成时）
"""
    args_schema: Type[BaseModel] = BusinessUnderstandingInput

    # Pydantic 字段声明（避免动态属性错误）
    storage: OntologyStorageV2 = Field(default_factory=OntologyStorageV2, exclude=True)

    # 五个核心问题（key, 问题文本, 提示信息）
    QUESTIONS: List[Tuple[str, str, str]] = [
        (
            "product_name",
            "你的产品是什么？",
            "请简要描述你的产品或服务，例如：'企业资源计划系统'、'在线教育平台'"
        ),
        (
            "business_model",
            "你的商业模式是什么？",
            "请说明你如何盈利，例如：'SaaS订阅模式'、'广告收入 + 会员费'"
        ),
        (
            "revenue_formula",
            "你的收入公式是什么？",
            "请描述核心收入计算方式，例如：'MRR × 客户数'、'客单价 × 订单数'"
        ),
        (
            "conversion_path",
            "你的转化路径是什么？",
            "请描述用户从接触到付费的路径，例如：'注册 → 试用 → 付费 → 续费'"
        ),
        (
            "key_metrics",
            "你最关心的3-5个指标是什么？",
            "请列举核心指标，例如：'MRR、Churn Rate、LTV、CAC、NPS'"
        )
    ]

    def _run_interactive(
        self,
        session_id: str,
        connection_name: str,
        answer: Optional[str] = None,
        skip_question: bool = False,
        **kwargs
    ) -> str:
        """
        执行业务理解交互

        Args:
            session_id: 会话ID（这里使用 connection_name 作为 session_id）
            connection_name: 数据库连接名
            answer: 用户答案
            skip_question: 是否跳过

        Returns:
            下一个问题或完成消息
        """
        # 使用 connection_name 作为 session_id（确保一致性）
        session_id = connection_name

        # 加载现有答案
        existing_answers = self._load_existing_answers(connection_name)

        # 处理用户输入
        if answer is not None or skip_question:
            current_question_index = self._get_current_question_index(existing_answers)
            if current_question_index < len(self.QUESTIONS):
                question_key = self.QUESTIONS[current_question_index][0]

                if skip_question:
                    # 跳过问题，标记为 "未知"
                    existing_answers[question_key] = "（用户跳过）"
                else:
                    # 保存答案
                    existing_answers[question_key] = answer.strip()

                # 保存到存储
                self.storage.update_business_context(connection_name, existing_answers)

        # 检查是否完成
        if len(existing_answers) >= len(self.QUESTIONS):
            return self._format_completion_message(connection_name, existing_answers)

        # 返回下一个问题
        next_question_index = len(existing_answers)
        return self._format_question(next_question_index, existing_answers)

    def _load_existing_answers(self, connection_name: str) -> Dict[str, str]:
        """加载已有答案"""
        context = self.storage.load_business_context(connection_name)
        if context:
            return context.get("answers", {})
        return {}

    def _get_current_question_index(self, answers: Dict[str, str]) -> int:
        """获取当前问题索引（即下一个要回答的问题）"""
        return len(answers)

    def _format_question(
        self,
        question_index: int,
        existing_answers: Dict[str, str]
    ) -> str:
        """格式化问题"""
        if question_index >= len(self.QUESTIONS):
            return "所有问题已回答完毕。"

        key, question_text, hint = self.QUESTIONS[question_index]

        # 构建消息
        message_parts = []

        # 进度提示
        message_parts.append(f"📋 **业务理解问卷** ({question_index + 1}/{len(self.QUESTIONS)})")
        message_parts.append("")

        # 已回答问题摘要（如果有）
        if existing_answers:
            message_parts.append("✅ **已回答：**")
            for i, (q_key, q_text, _) in enumerate(self.QUESTIONS[:question_index]):
                answer = existing_answers.get(q_key, "（未回答）")
                message_parts.append(f"  {i + 1}. {q_text}")
                message_parts.append(f"     → {answer}")
            message_parts.append("")

        # 当前问题
        message_parts.append(f"❓ **问题 {question_index + 1}：{question_text}**")
        message_parts.append(f"💡 提示：{hint}")
        message_parts.append("")
        message_parts.append("请直接回答问题，或输入'跳过'如果暂时不清楚。")

        return "\n".join(message_parts)

    def _format_completion_message(
        self,
        connection_name: str,
        answers: Dict[str, str]
    ) -> str:
        """格式化完成消息"""
        message_parts = []

        message_parts.append("✅ **业务理解完成！**")
        message_parts.append("")
        message_parts.append("感谢你的回答！以下是你的业务上下文：")
        message_parts.append("")

        # 汇总答案
        for i, (key, question_text, _) in enumerate(self.QUESTIONS):
            answer = answers.get(key, "（未回答）")
            message_parts.append(f"**{i + 1}. {question_text}**")
            message_parts.append(f"   {answer}")
            message_parts.append("")

        # 保存位置
        message_parts.append(f"📁 业务上下文已保存到：")
        message_parts.append(f"   `ontology_store/{connection_name}/business_context.json`")
        message_parts.append("")

        # 下一步提示
        message_parts.append("🚀 **下一步：**")
        message_parts.append("   现在可以开始构建本体了！请使用 `OntologyBuilder` 工具。")

        return "\n".join(message_parts)

    def get_answers(self, connection_name: str) -> Optional[Dict[str, str]]:
        """
        获取已保存的业务理解答案（工具方法，供其他工具调用）

        Args:
            connection_name: 数据库连接名

        Returns:
            答案字典，不存在时返回None
        """
        context = self.storage.load_business_context(connection_name)
        if context:
            return context.get("answers")
        return None

    def is_completed(self, connection_name: str) -> bool:
        """
        检查业务理解是否完成（工具方法，供其他工具调用）

        Args:
            connection_name: 数据库连接名

        Returns:
            是否完成
        """
        return self.storage.is_business_context_completed(connection_name)

    def reset(self, connection_name: str) -> str:
        """
        重置业务理解（清除所有答案，重新开始）

        Args:
            connection_name: 数据库连接名

        Returns:
            重置确认消息
        """
        # 清除文件
        context_file = self.storage.base_path / connection_name / "business_context.json"
        if context_file.exists():
            context_file.unlink()

        # 清除交互状态
        self._clear_state(connection_name)

        return f"✅ 已重置 {connection_name} 的业务理解问卷，可以重新开始。"
