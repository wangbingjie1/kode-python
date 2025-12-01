"""
本体描述自动更新服务

当用户回答不确定性问题后，自动更新本体中的实体描述。
支持表级别和字段级别的描述更新。
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from kode.core.model_manager import ModelManager
from kode.tools.ontology_update.update_tool import OntologyUpdateTool

logger = logging.getLogger(__name__)

# AI 描述合并提示词
DESCRIPTION_MERGE_PROMPT = """
你是本体知识提取专家。从用户答案中提取关键信息并更新实体描述。

## 上下文
- **实体名称**: {entity_name}
- **实体级别**: {entity_level}
- **当前描述**: {current_description}
- **问题**: {question}
- **用户答案**: {answer}

## 任务
1. **提取关键信息**：从用户答案中提取与该实体相关的核心知识
   - 产品归属（如 "glbgpt产品的"）
   - 业务场景（如 "用于充值订单"）
   - 使用范围（如 "仅在XX模块使用"）
   - 枚举值（如字段支持的所有可能值）
   - 废弃/新增状态（如 "已废弃" 或 "新增"）

2. **智能合并**：
   - 保留当前描述中的核心业务逻辑
   - 补充用户答案中的新知识
   - 如果有冲突，以用户答案为准
   - 保持简洁（建议50字以内）

3. **特殊处理**：
   - 表级别：重点关注产品归属、业务范围、使用场景
   - 字段级别：重点关注枚举值、取值范围、业务含义

## 输出格式（严格JSON）
{{
  "updated_description": "合并后的描述文本",
  "extracted_info": "提取的关键信息摘要",
  "is_conflict": false,
  "reasoning": "合并理由（为什么这样合并）"
}}

注意：
- 必须返回严格的JSON格式
- updated_description 不能为空
- 如果无法提取有效信息，返回原描述
"""


class OntologyDescriptionUpdater:
    """本体描述自动更新器"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.ontology_update_tool = OntologyUpdateTool()

    def _extract_entities_from_uncertainty(self, entity_str: str) -> Dict[str, Any]:
        """
        从不确定性的 entity 字段提取实体信息

        支持三种格式：
        1. 表级别（单个）: "order" → {"level": "table", "main_table": "order"}
        2. 表级别（多个）: "order vs platform_trade_order" → {"level": "table", "main_table": "order", ...}
        3. 字段级别（单个）: "platform_user_account.type" → {"level": "field", "main_table": "platform_user_account", "main_field": "type"}
        4. 字段级别（多个）: "platform_user.id vs platform_user_account.user_id" → {"level": "field", ...}

        Returns:
            {
                "level": "table" | "field",
                "main_table": str,
                "main_field": Optional[str],
                "related_entities": List[str]
            }
        """
        entity_str = entity_str.strip()

        # 检测字段级别（包含 .）
        if "." in entity_str:
            # 提取所有 table.field 模式
            parts = re.findall(r"(\w+)\.(\w+)", entity_str)
            if parts:
                main_table, main_field = parts[0]
                related = [f"{t}.{f}" for t, f in parts[1:]]
                return {
                    "level": "field",
                    "main_table": main_table,
                    "main_field": main_field,
                    "related_entities": related,
                }

        # 表级别：提取所有表名（过滤连接词）
        tables = re.findall(r"(\w+)", entity_str)
        tables = [t for t in tables if t.lower() not in ["vs", "and", "or", "the"]]

        if not tables:
            return {
                "level": "unknown",
                "main_table": "",
                "main_field": None,
                "related_entities": [],
            }

        return {
            "level": "table",
            "main_table": tables[0],
            "main_field": None,
            "related_entities": tables[1:],
        }

    def _locate_entity_in_ontology(
        self, ontology: Dict, table_name: str
    ) -> Optional[Dict]:
        """
        在本体的 classes[] 数组中定位表实体

        匹配规则：
        1. 优先匹配 technical_name
        2. 其次匹配 table_mapping

        Args:
            ontology: 本体数据（V2格式，classes是数组）
            table_name: 表名（如 "order", "platform_user_account"）

        Returns:
            找到的 class 定义字典，未找到返回 None
        """
        classes = ontology.get("classes", [])
        if not isinstance(classes, list):
            logger.warning("本体格式错误：classes 不是数组")
            return None

        for cls in classes:
            # 优先匹配 technical_name
            if cls.get("technical_name") == table_name:
                return cls
            # 次优匹配 table_mapping
            if cls.get("table_mapping") == table_name:
                return cls

        return None

    def _locate_field_in_ontology(
        self, ontology: Dict, table_name: str, field_name: str
    ) -> Optional[Dict]:
        """
        在本体的 classes[].properties[] 中定位字段

        流程：
        1. 先定位到表实体
        2. 在 properties[] 数组中查找字段
        3. 匹配规则：technical_name 或 column_mapping

        Returns:
            找到的 property 定义字典，未找到返回 None
        """
        class_obj = self._locate_entity_in_ontology(ontology, table_name)
        if not class_obj:
            logger.warning(f"未找到表实体: {table_name}")
            return None

        properties = class_obj.get("properties", [])
        if not isinstance(properties, list):
            logger.warning(f"表 {table_name} 的 properties 不是数组")
            return None

        for prop in properties:
            # 优先匹配 technical_name
            if prop.get("technical_name") == field_name:
                return prop
            # 次优匹配 column_mapping
            if prop.get("column_mapping") == field_name:
                return prop

        return None

    async def _generate_merged_description(
        self,
        entity_name: str,
        entity_level: str,
        current_desc: str,
        question: str,
        answer: str,
    ) -> Dict[str, Any]:
        """
        调用 AI 模型生成合并后的描述

        Returns:
            {
                "updated_description": str,
                "extracted_info": str,
                "is_conflict": bool,
                "reasoning": str
            }
        """
        prompt = DESCRIPTION_MERGE_PROMPT.format(
            entity_name=entity_name,
            entity_level=entity_level,
            current_description=current_desc or "（无描述）",
            question=question,
            answer=answer,
        )

        try:
            # 使用 quick 模型快速处理
            model = self.model_manager.get_model("quick")
            response = await model.ainvoke(prompt)

            # 解析响应（可能是 Markdown 包裹的 JSON）
            content = response.content if hasattr(response, "content") else str(response)

            # 移除可能的 Markdown 代码块标记
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*$", "", content)
            content = content.strip()

            result = json.loads(content)

            # 验证必需字段
            if not result.get("updated_description"):
                logger.warning("AI 返回的 updated_description 为空，使用原描述")
                result["updated_description"] = current_desc

            return result

        except json.JSONDecodeError as e:
            logger.error(f"AI 响应 JSON 解析失败: {e}\n内容: {content}")
            return {
                "updated_description": current_desc,
                "extracted_info": "",
                "is_conflict": False,
                "reasoning": "AI响应解析失败，保留原描述",
            }
        except Exception as e:
            logger.error(f"调用 AI 模型失败: {e}", exc_info=True)
            return {
                "updated_description": current_desc,
                "extracted_info": "",
                "is_conflict": False,
                "reasoning": "AI调用失败，保留原描述",
            }

    async def update_from_answer(
        self,
        connection_name: str,
        uncertainty: Dict,
        answer: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从不确定性回答中更新本体实体描述

        Args:
            connection_name: 数据库连接名
            uncertainty: 不确定性问题对象（包含 entity, question 等字段）
            answer: 用户的答案
            conversation_id: 对话ID（用于记录变更）

        Returns:
            {
                "status": "success" | "skip" | "error",
                "entity": str,
                "level": "table" | "field",
                "new_description": str,
                "message": str
            }
        """
        try:
            entity_str = uncertainty.get("entity", "")
            question = uncertainty.get("question", "")

            logger.info(f"[OntologyUpdater] 开始处理不确定性回答:")
            logger.info(f"  - entity: {entity_str}")
            logger.info(f"  - question: {question[:100]}...")
            logger.info(f"  - answer: {answer[:100]}...")

            if not entity_str:
                return {
                    "status": "skip",
                    "entity": "",
                    "level": "unknown",
                    "message": "不确定性问题缺少 entity 字段",
                }

            # 1. 提取实体信息
            entity_info = self._extract_entities_from_uncertainty(entity_str)
            level = entity_info["level"]
            main_table = entity_info["main_table"]
            main_field = entity_info.get("main_field")

            logger.info(f"[OntologyUpdater] 实体解析结果: level={level}, main_table={main_table}, main_field={main_field}")

            if level == "unknown":
                return {
                    "status": "skip",
                    "entity": entity_str,
                    "level": "unknown",
                    "message": f"无法解析实体: {entity_str}",
                }

            # 2. 加载本体文件
            ontology_file = Path("ontology_store") / connection_name / "ontology_v2.json"
            logger.info(f"[OntologyUpdater] 加载本体文件: {ontology_file}")

            if not ontology_file.exists():
                return {
                    "status": "skip",
                    "entity": entity_str,
                    "level": level,
                    "message": f"本体文件不存在: {ontology_file}",
                }

            with open(ontology_file, "r", encoding="utf-8") as f:
                ontology = json.load(f)

            # 3. 定位目标实体/字段
            if level == "table":
                target_obj = self._locate_entity_in_ontology(ontology, main_table)
                logger.info(f"[OntologyUpdater] 定位表实体: {main_table}, 结果: {'找到' if target_obj else '未找到'}")

                if not target_obj:
                    return {
                        "status": "skip",
                        "entity": main_table,
                        "level": "table",
                        "message": f"本体中未找到表: {main_table}",
                    }

                entity_name = f"{target_obj.get('name', main_table)} ({main_table})"
                current_desc = target_obj.get("description", "")
                target_path = f"classes.{main_table}.description"
                change_type = "update_class_desc"

            else:  # field level
                target_obj = self._locate_field_in_ontology(
                    ontology, main_table, main_field
                )
                logger.info(f"[OntologyUpdater] 定位字段: {main_table}.{main_field}, 结果: {'找到' if target_obj else '未找到'}")

                if not target_obj:
                    return {
                        "status": "skip",
                        "entity": f"{main_table}.{main_field}",
                        "level": "field",
                        "message": f"本体中未找到字段: {main_table}.{main_field}",
                    }

                entity_name = f"{target_obj.get('name', main_field)} ({main_table}.{main_field})"
                current_desc = target_obj.get("description", "")
                target_path = f"classes.{main_table}.properties.{main_field}.description"
                change_type = "update_property_desc"

            logger.info(f"[OntologyUpdater] 当前描述: {current_desc[:100]}...")
            logger.info(f"[OntologyUpdater] 开始调用AI生成合并后的描述...")

            # 4. AI 生成合并后的描述
            merge_result = await self._generate_merged_description(
                entity_name=entity_name,
                entity_level=level,
                current_desc=current_desc,
                question=question,
                answer=answer,
            )

            new_description = merge_result["updated_description"]
            logger.info(f"[OntologyUpdater] AI生成的新描述: {new_description[:100]}...")
            logger.info(f"[OntologyUpdater] 提取的信息: {merge_result.get('extracted_info', '')}")

            # 5. 调用本体更新工具
            update_input = {
                "connection_name": connection_name,
                "change_type": change_type,
                "target_path": target_path,
                "new_value": new_description,
                "user_intent": f"用户回答不确定性问题: {question}",
                "conversation_id": conversation_id,
            }

            logger.info(f"[OntologyUpdater] 调用本体更新工具: change_type={change_type}, target_path={target_path}")
            update_result = await self.ontology_update_tool._arun(**update_input)
            logger.info(f"[OntologyUpdater] 更新工具返回: {update_result}")

            logger.info(
                f"✅ 本体描述已更新 [{level}]: {entity_str}\n"
                f"   原描述: {current_desc[:50]}...\n"
                f"   新描述: {new_description[:50]}...\n"
                f"   提取信息: {merge_result.get('extracted_info', '')}"
            )

            return {
                "status": "success",
                "entity": entity_str,
                "level": level,
                "new_description": new_description,
                "extracted_info": merge_result.get("extracted_info", ""),
                "reasoning": merge_result.get("reasoning", ""),
                "message": update_result,
            }

        except Exception as e:
            logger.error(f"❌ 更新本体描述失败: {e}", exc_info=True)
            return {
                "status": "error",
                "entity": entity_str if "entity_str" in locals() else "",
                "level": level if "level" in locals() else "unknown",
                "message": str(e),
            }
