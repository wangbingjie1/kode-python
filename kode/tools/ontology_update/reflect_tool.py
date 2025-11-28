"""
Ontology Reflect Tool

本体反思工具：当用户回答不确定性问题后，自动检测并更新本体
"""

from typing import Dict, Any, Optional, Type, List
from pydantic import BaseModel, Field
import json

from kode.tools.base import KodeTool
from kode.tools.ontology_update.update_tool import OntologyUpdateTool
from kode.tools.ontology_update import update_tool as ontology_update_module
from kode.utils.logger import get_logger

logger = get_logger(__name__)


class OntologyReflectToolInput(BaseModel):
    """本体反思工具输入参数"""

    connection_name: str = Field(description="数据库连接名称")
    domain_name: str = Field(description="业务域名称（从不确定性问题中获取）")
    question: str = Field(description="用户回答的不确定性问题")
    answer: str = Field(description="用户的回答内容")
    related_entities: List[str] = Field(
        default=[],
        description="相关实体列表（类名或属性路径），如 ['Order', 'Order.status']"
    )


class OntologyReflectTool(KodeTool):
    """
    本体反思工具

    功能：
    1. 接收用户对不确定性问题的回答
    2. 分析回答是否与现有本体冲突
    3. 自动生成修正建议
    4. 调用 OntologyUpdateTool 应用修正

    使用场景：
    - 用户回答"订单状态有哪些？"后，检查答案中的状态是否都在本体中
    - 用户回答"用户等级的含义是什么？"后，检查是否与本体中的描述一致
    - 用户回答业务规则相关问题后，检查本体中是否已记录
    """

    name: str = "OntologyReflectTool"
    description: str = (
        "分析用户对不确定性问题的回答，检测与现有本体的冲突并自动修正。\n"
        "当用户回答了关于枚举值、字段含义、业务规则等问题后调用此工具。\n\n"
        "**工作流程**：\n"
        "1. 获取当前本体中相关实体的定义\n"
        "2. 对比用户回答与本体定义\n"
        "3. 识别冲突（缺失的枚举值、错误的描述等）\n"
        "4. 生成修正建议\n"
        "5. 自动调用 OntologyUpdateTool 应用修正\n\n"
        "**示例**：\n"
        "问题：'订单状态有哪些？'\n"
        "回答：'待支付、已支付、已发货、已取消'\n"
        "→ 检测到'已取消'在本体中缺失，自动添加"
    )
    args_schema: Type[BaseModel] = OntologyReflectToolInput
    requires_permission: bool = False

    def _run(
        self,
        connection_name: str,
        domain_name: str,
        question: str,
        answer: str,
        related_entities: List[str] = None,
    ) -> str:
        """
        执行本体反思

        Args:
            connection_name: 数据库连接名称
            domain_name: 业务域名称
            question: 不确定性问题
            answer: 用户回答
            related_entities: 相关实体列表

        Returns:
            反思结果（JSON字符串）
        """
        related_entities = related_entities or []

        try:
            logger.info(f"🤔 开始反思: domain={domain_name}, question={question}")

            # 1. 获取本体管理器
            manager = ontology_update_module._GLOBAL_MANAGERS.get(connection_name)
            if not manager:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"未找到连接 {connection_name} 的本体管理器",
                    },
                    ensure_ascii=False,
                )

            ontology = manager.get_ontology()

            # 2. 提取当前本体中相关实体的定义
            current_state = self._extract_current_state(ontology, related_entities)

            # 3. 使用 AI 分析冲突（通过 Extended Thinking）
            conflicts = self._ai_analyze_conflicts(
                question, answer, current_state, ontology
            )

            if not conflicts:
                logger.info("✅ 未检测到冲突，本体与用户回答一致")
                return json.dumps(
                    {
                        "status": "success",
                        "conflicts_found": False,
                        "message": "用户回答与现有本体一致，无需更新",
                    },
                    ensure_ascii=False,
                )

            # 4. 应用修正
            update_tool = OntologyUpdateTool()
            applied_changes = []

            for conflict in conflicts:
                logger.info(f"🔧 应用修正: {conflict['description']}")

                result_json = update_tool._run(
                    connection_name=connection_name,
                    change_type=conflict["change_type"],
                    target_path=conflict["target_path"],
                    new_value=conflict["new_value"],
                    old_value=conflict.get("old_value"),
                    user_intent=f"反思修正: {question} - {conflict['description']}",
                )

                result = json.loads(result_json)
                if result["status"] == "success":
                    applied_changes.append(conflict["description"])
                    logger.info(f"✅ 修正成功: {conflict['description']}")
                else:
                    logger.warning(f"❌ 修正失败: {conflict['description']}")

            return json.dumps(
                {
                    "status": "success",
                    "conflicts_found": True,
                    "conflicts_count": len(conflicts),
                    "applied_changes": applied_changes,
                    "message": f"✅ 已应用 {len(applied_changes)} 项修正",
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"❌ 本体反思失败: {e}", exc_info=True)
            return json.dumps(
                {"status": "error", "message": f"反思失败: {str(e)}"},
                ensure_ascii=False,
            )

    def _extract_current_state(
        self, ontology: Dict[str, Any], related_entities: List[str]
    ) -> Dict[str, Any]:
        """
        提取本体中相关实体的当前状态

        Args:
            ontology: 完整本体
            related_entities: 相关实体列表

        Returns:
            当前状态字典
        """
        current_state = {}

        for entity in related_entities:
            parts = entity.split(".")

            if len(parts) == 1:
                # 类级别: "Order"
                class_name = parts[0]
                if class_name in ontology.get("classes", {}):
                    current_state[entity] = ontology["classes"][class_name]

            elif len(parts) == 2:
                # 属性级别: "Order.status"
                class_name, prop_name = parts
                class_def = ontology.get("classes", {}).get(class_name, {})
                prop_def = class_def.get("properties", {}).get(prop_name, {})
                if prop_def:
                    current_state[entity] = prop_def

        return current_state

    def _ai_analyze_conflicts(
        self,
        question: str,
        answer: str,
        current_state: Dict[str, Any],
        ontology: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        使用启发式规则分析冲突

        这个方法使用简单的规则匹配。
        在实际应用中，可以调用 AI 模型进行更智能的分析。

        Args:
            question: 问题
            answer: 回答
            current_state: 当前本体状态
            ontology: 完整本体

        Returns:
            冲突列表，每个冲突包含 change_type, target_path, new_value 等
        """
        conflicts = []

        # 规则1：检测枚举值缺失
        # 问题模式："XX有哪些？"、"XX的值是什么？"
        if any(keyword in question for keyword in ["有哪些", "枚举值", "选项", "状态"]):
            conflicts.extend(
                self._detect_missing_enum_values(answer, current_state, ontology)
            )

        # 规则2：检测描述不一致
        # 问题模式："XX是什么意思？"、"XX的含义？"
        if any(keyword in question for keyword in ["是什么", "含义", "意思", "解释"]):
            conflicts.extend(
                self._detect_description_mismatch(answer, current_state, question)
            )

        return conflicts

    def _detect_missing_enum_values(
        self, answer: str, current_state: Dict[str, Any], ontology: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检测缺失的枚举值"""
        conflicts = []

        # 简单实现：从回答中提取可能的枚举值（用顿号、逗号分隔）
        import re

        # 提取枚举值（支持中文顿号、逗号、分号）
        enum_candidates = re.split(r"[、，,;；]", answer.strip())
        enum_candidates = [e.strip() for e in enum_candidates if e.strip()]

        # 检查每个候选值是否在本体中
        for entity_path, entity_def in current_state.items():
            if "enum_values" in entity_def:
                existing_values = [ev.get("label", ev.get("value", "")) for ev in entity_def["enum_values"]]

                # 检测缺失
                for candidate in enum_candidates:
                    if candidate not in existing_values and len(candidate) < 10:  # 忽略过长的文本
                        # 构建正确的 target_path（需要包含 classes. 前缀）
                        parts = entity_path.split(".")
                        if len(parts) == 2:
                            # Order.status -> classes.Order.properties.status.enum_values
                            target_path = f"classes.{parts[0]}.properties.{parts[1]}.enum_values"
                        else:
                            target_path = f"{entity_path}.enum_values"

                        # 推测这是缺失的枚举值
                        conflicts.append(
                            {
                                "change_type": "add_enum_value",
                                "target_path": target_path,
                                "new_value": {"value": candidate, "label": candidate},
                                "old_value": None,
                                "description": f"添加枚举值 '{candidate}' 到 {entity_path}",
                            }
                        )

        return conflicts

    def _detect_description_mismatch(
        self, answer: str, current_state: Dict[str, Any], question: str
    ) -> List[Dict[str, Any]]:
        """检测描述不一致"""
        conflicts = []

        # 简单实现：如果用户回答与当前描述差异很大，建议更新
        for entity_path, entity_def in current_state.items():
            current_desc = entity_def.get("business_description", "")

            # 如果当前描述为空，或与用户回答差异很大
            if not current_desc or (current_desc not in answer and answer not in current_desc):
                # 提取问题中的字段名
                parts = entity_path.split(".")
                if len(parts) == 2:
                    # 属性级别: User.level -> classes.User.properties.level.business_description
                    target_path = f"classes.{parts[0]}.properties.{parts[1]}.business_description"
                    conflicts.append(
                        {
                            "change_type": "update_property_desc",
                            "target_path": target_path,
                            "new_value": answer.strip(),
                            "old_value": current_desc,
                            "description": f"更新 {entity_path} 的业务描述",
                        }
                    )

        return conflicts
