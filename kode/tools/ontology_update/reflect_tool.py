"""
Ontology Reflect Tool

本体反思工具：当用户回答不确定性问题后，自动检测并更新本体
"""

from typing import Dict, Any, Optional, Type, List
from pydantic import BaseModel, Field
import json

from langchain_core.messages import HumanMessage

from kode.tools.base import KodeTool
from kode.tools.ontology_update.update_tool import OntologyUpdateTool
from kode.tools.ontology_update import update_tool as ontology_update_module
from kode.core.model_manager import ModelManager
from kode.utils.config import ConfigManager
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
        使用 AI 分析用户回答与本体的冲突

        Args:
            question: 问题
            answer: 回答
            current_state: 当前本体状态
            ontology: 完整本体

        Returns:
            冲突列表，每个冲突包含 change_type, target_path, new_value 等
        """
        # 1. 获取模型
        config_manager = ConfigManager()
        model_manager = ModelManager(config_manager.get_all())
        model = model_manager.get_model("quick")
        model.temperature = 0.0  # 确定性输出

        # 2. 构造 prompt
        prompt = self._build_conflict_analysis_prompt(
            question, answer, current_state, ontology
        )

        # 3. 调用 AI
        logger.info("🤖 调用 AI 分析冲突...")
        response = model.invoke([HumanMessage(content=prompt)])
        logger.info(f"AI 响应: {response.content[:500]}")

        # 4. 提取 JSON
        conflicts = self._extract_json_from_text(response.content)

        if conflicts is None:
            raise ValueError(f"AI 返回无效 JSON: {response.content[:200]}")

        # 5. 验证和标准化
        return self._validate_conflicts(conflicts)

    def _build_conflict_analysis_prompt(
        self,
        question: str,
        answer: str,
        current_state: Dict[str, Any],
        ontology: Dict[str, Any],
    ) -> str:
        """构造冲突分析 prompt"""

        # 提取本体中所有类的简要信息（用于上下文）
        classes_summary = []
        for class_name, class_def in ontology.get("classes", {}).items():
            props = list(class_def.get("properties", {}).keys())[:5]
            classes_summary.append(f"- {class_name}: {', '.join(props)}")

        ontology_overview = "\n".join(classes_summary[:20])  # 最多20个类

        return f"""你是本体专家，分析用户回答与现有本体定义之间的冲突。

## 问题
{question}

## 用户回答
{answer}

## 当前本体中相关实体定义
```json
{json.dumps(current_state, ensure_ascii=False, indent=2)}
```

## 本体概览（部分类和属性）
{ontology_overview}

## 任务
对比用户回答与本体定义，识别以下类型的冲突：

1. **枚举值缺失** (add_enum_value) - 用户提到的枚举值在本体中不存在
2. **枚举值错误** (update_enum_value) - 本体中的枚举值与用户描述不符
3. **描述不一致** (update_property_desc) - 业务描述需要根据用户回答更新
4. **新增属性** (add_property) - 用户提到了本体中没有的属性

## 输出格式
只返回 JSON 数组，不要其他内容。每个冲突包含：
- change_type: "add_enum_value" | "update_enum_value" | "update_property_desc" | "add_property"
- target_path: 本体路径，格式如 "classes.Order.properties.status.enum_values"
- new_value: 新值（枚举值用 {{"value": "xxx", "label": "xxx"}} 格式）
- old_value: 旧值（可选，用于 update 类型）
- description: 冲突描述（中文）

如果没有冲突，返回空数组 []

示例输出：
```json
[
  {{
    "change_type": "add_enum_value",
    "target_path": "classes.Order.properties.status.enum_values",
    "new_value": {{"value": "cancelled", "label": "已取消"}},
    "old_value": null,
    "description": "添加枚举值 '已取消' 到 Order.status"
  }}
]
```
"""

    def _extract_json_from_text(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """从 AI 输出提取 JSON（三层策略）"""

        # 策略1：直接解析
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 策略2：查找 [ ] 边界
        start_idx = text.find("[")
        end_idx = text.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                potential_json = text[start_idx : end_idx + 1]
                result = json.loads(potential_json)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 策略3：markdown 代码块
        if "```" in text:
            try:
                # 找 ```json 或 ```
                if "```json" in text:
                    code_start = text.find("```json") + 7
                else:
                    code_start = text.find("```") + 3

                json_start = text.find("\n", code_start) + 1
                code_end = text.find("```", json_start)
                if code_end != -1:
                    json_text = text[json_start:code_end].strip()
                    result = json.loads(json_text)
                    if isinstance(result, list):
                        return result
            except (json.JSONDecodeError, ValueError):
                pass

        logger.warning(f"无法提取 JSON: {text[:200]}")
        return None

    def _validate_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证冲突格式，过滤无效项"""
        valid_change_types = {
            "add_enum_value",
            "update_enum_value",
            "update_property_desc",
            "add_property",
        }

        validated = []
        for conflict in conflicts:
            # 必须有 change_type
            if conflict.get("change_type") not in valid_change_types:
                logger.warning(f"跳过无效 change_type: {conflict}")
                continue

            # 必须有 target_path
            if not conflict.get("target_path"):
                logger.warning(f"跳过缺少 target_path: {conflict}")
                continue

            # 必须有 new_value
            if "new_value" not in conflict:
                logger.warning(f"跳过缺少 new_value: {conflict}")
                continue

            # 必须有 description
            if not conflict.get("description"):
                conflict["description"] = f"{conflict['change_type']} at {conflict['target_path']}"

            validated.append(conflict)

        return validated
