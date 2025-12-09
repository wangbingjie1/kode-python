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

# AI 描述合并提示词（支持多实体对比）
DESCRIPTION_MERGE_PROMPT = """
你是本体知识提取专家。从用户答案中提取关键信息并更新实体描述。

## 上下文
- **当前实体**: {current_entity}
- **实体名称**: {entity_name}
- **实体级别**: {entity_level}
- **当前描述**: {current_description}
- **问题**: {question}
- **用户答案**: {answer}
- **涉及的所有实体**: {all_entities}

## 核心原则
**严禁推测**：只使用用户答案中明确提到的信息，不要自己推断或添加用户没说的内容。

## 任务
1. **理解多实体对比**：
   - 如果问题涉及多个实体对比（如 "order vs platform_trade_order"）
   - 用户的答案通常会说明每个实体的区别和用途
   - 你需要针对**当前实体** ({current_entity}) 提取专属于它的信息

2. **提取关键信息**：从用户答案中提取与**当前实体**相关的核心知识
   - 只提取用户**明确说明**的信息
   - 不要推测用户没提到的状态（如"已下线"、"历史表"等）
   - 不要添加用户答案中没有的修饰词

3. **智能合并**：
   - 保留当前描述中的核心业务逻辑
   - 补充用户答案中针对**当前实体**的新知识
   - 如果有冲突，以用户答案为准
   - 保持简洁（建议50字以内）

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
- **绝对不要添加用户答案中没有的信息**
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
        在本体中定位表实体，支持 v2 和 v3 两种格式

        V2 格式：classes 是数组，每个元素有 technical_name/table_mapping
        V3 格式：schema.classes 是嵌套字典，domain -> table_name -> table_def

        Args:
            ontology: 本体数据
            table_name: 表名（如 "order", "platform_user_account"）

        Returns:
            找到的 class 定义字典，未找到返回 None
        """
        version = ontology.get("version", "2.0")

        # V3 格式：嵌套在 schema.classes 下，按域分组
        if version.startswith("3"):
            schema = ontology.get("schema", {})
            classes = schema.get("classes", {})

            if not isinstance(classes, dict):
                logger.warning("V3 本体格式错误：schema.classes 不是字典")
                return None

            # 遍历所有域
            for domain_name, domain_tables in classes.items():
                if not isinstance(domain_tables, dict):
                    continue
                # 在域内查找表
                if table_name in domain_tables:
                    table_def = domain_tables[table_name]
                    # 添加额外信息便于后续处理
                    table_def["_domain"] = domain_name
                    table_def["_table_name"] = table_name
                    return table_def

            return None

        # V2 格式：classes 是数组
        classes = ontology.get("classes", [])
        if not isinstance(classes, list):
            logger.warning("V2 本体格式错误：classes 不是数组")
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
        在本体中定位字段，支持 v2 和 v3 两种格式

        V2 格式：classes[].properties[] 数组
        V3 格式：schema.classes.{domain}.{table}.attributes 字典

        Returns:
            找到的属性定义字典，未找到返回 None
        """
        class_obj = self._locate_entity_in_ontology(ontology, table_name)
        if not class_obj:
            logger.warning(f"未找到表实体: {table_name}")
            return None

        version = ontology.get("version", "2.0")

        # V3 格式：attributes 是字典
        if version.startswith("3"):
            attributes = class_obj.get("attributes", {})
            if not isinstance(attributes, dict):
                logger.warning(f"V3 表 {table_name} 的 attributes 不是字典")
                return None

            if field_name in attributes:
                field_def = attributes[field_name]
                # 添加额外信息便于后续处理
                field_def["_field_name"] = field_name
                field_def["_table_name"] = table_name
                return field_def

            return None

        # V2 格式：properties 是数组
        properties = class_obj.get("properties", [])
        if not isinstance(properties, list):
            logger.warning(f"V2 表 {table_name} 的 properties 不是数组")
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
        all_entities: Optional[List[str]] = None,
        current_entity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        调用 AI 模型生成合并后的描述

        Args:
            entity_name: 实体的显示名称
            entity_level: "table" 或 "field"
            current_desc: 当前的描述
            question: 不确定性问题
            answer: 用户的答案
            all_entities: 所有涉及的实体列表（用于多实体对比）
            current_entity: 当前正在更新的实体名称

        Returns:
            {
                "updated_description": str,
                "extracted_info": str,
                "is_conflict": bool,
                "reasoning": str
            }
        """
        # 构建多实体上下文
        all_entities_str = ", ".join(all_entities) if all_entities else entity_name
        current_entity_str = current_entity or entity_name

        prompt = DESCRIPTION_MERGE_PROMPT.format(
            entity_name=entity_name,
            entity_level=entity_level,
            current_description=current_desc or "（无描述）",
            question=question,
            answer=answer,
            all_entities=all_entities_str,
            current_entity=current_entity_str,
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

        支持同时更新多个相关实体（如 "order vs platform_trade_order"）

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
                "message": str,
                "updated_entities": List[str]  # 所有更新的实体列表
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
            related_entities = entity_info.get("related_entities", [])

            logger.info(f"[OntologyUpdater] 实体解析结果: level={level}, main_table={main_table}, main_field={main_field}, related={related_entities}")

            if level == "unknown":
                return {
                    "status": "skip",
                    "entity": entity_str,
                    "level": "unknown",
                    "message": f"无法解析实体: {entity_str}",
                }

            # 2. 加载本体文件（优先 v3，回退到 v2）
            ontology_base = Path("ontology_store") / connection_name
            ontology_file = ontology_base / "ontology_v3.json"
            if not ontology_file.exists():
                ontology_file = ontology_base / "ontology_v2.json"
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

            version = ontology.get("version", "2.0")
            is_v3 = version.startswith("3")

            # 3. 构建需要更新的实体列表
            all_tables = [main_table] + related_entities
            update_results = []
            updated_entities = []

            for table_name in all_tables:
                result = await self._update_single_entity(
                    ontology=ontology,
                    is_v3=is_v3,
                    connection_name=connection_name,
                    table_name=table_name,
                    field_name=main_field if level == "field" else None,
                    level=level,
                    question=question,
                    answer=answer,
                    all_entities=all_tables,  # 传递所有实体，让 AI 知道上下文
                    conversation_id=conversation_id,
                )
                update_results.append(result)
                if result.get("status") == "success":
                    updated_entities.append(table_name)

            # 4. 汇总结果
            success_count = len([r for r in update_results if r.get("status") == "success"])
            if success_count == 0:
                return {
                    "status": "skip",
                    "entity": entity_str,
                    "level": level,
                    "message": f"所有实体更新失败: {[r.get('message') for r in update_results]}",
                    "updated_entities": [],
                }

            return {
                "status": "success",
                "entity": entity_str,
                "level": level,
                "new_description": update_results[0].get("new_description", ""),
                "message": f"成功更新 {success_count}/{len(all_tables)} 个实体",
                "updated_entities": updated_entities,
                "details": update_results,
            }

        except Exception as e:
            logger.error(f"❌ 更新本体描述失败: {e}", exc_info=True)
            return {
                "status": "error",
                "entity": entity_str if "entity_str" in locals() else "",
                "level": level if "level" in locals() else "unknown",
                "message": str(e),
            }

    async def _update_single_entity(
        self,
        ontology: Dict,
        is_v3: bool,
        connection_name: str,
        table_name: str,
        field_name: Optional[str],
        level: str,
        question: str,
        answer: str,
        all_entities: List[str],
        conversation_id: Optional[str],
    ) -> Dict[str, Any]:
        """更新单个实体的描述"""
        try:
            if level == "table":
                target_obj = self._locate_entity_in_ontology(ontology, table_name)
                logger.info(f"[OntologyUpdater] 定位表实体: {table_name}, 结果: {'找到' if target_obj else '未找到'}")

                if not target_obj:
                    return {
                        "status": "skip",
                        "entity": table_name,
                        "level": "table",
                        "message": f"本体中未找到表: {table_name}",
                    }

                entity_name = f"{target_obj.get('name', table_name)} ({table_name})"
                current_desc = target_obj.get("description", "")

                if is_v3:
                    domain = target_obj.get("_domain", "unknown")
                    target_path = f"schema.classes.{domain}.{table_name}.description"
                else:
                    target_path = f"classes.{table_name}.description"
                change_type = "update_class_desc"

            else:  # field level
                target_obj = self._locate_field_in_ontology(ontology, table_name, field_name)
                logger.info(f"[OntologyUpdater] 定位字段: {table_name}.{field_name}, 结果: {'找到' if target_obj else '未找到'}")

                if not target_obj:
                    return {
                        "status": "skip",
                        "entity": f"{table_name}.{field_name}",
                        "level": "field",
                        "message": f"本体中未找到字段: {table_name}.{field_name}",
                    }

                entity_name = f"{target_obj.get('name', field_name)} ({table_name}.{field_name})"
                if is_v3:
                    current_desc = target_obj.get("constraint", "") or target_obj.get("why", "")
                else:
                    current_desc = target_obj.get("description", "")

                if is_v3:
                    table_obj = self._locate_entity_in_ontology(ontology, table_name)
                    domain = table_obj.get("_domain", "unknown") if table_obj else "unknown"
                    target_path = f"schema.classes.{domain}.{table_name}.attributes.{field_name}.constraint"
                else:
                    target_path = f"classes.{table_name}.properties.{field_name}.description"
                change_type = "update_property_desc"

            logger.info(f"[OntologyUpdater] 实体 {table_name} 当前描述: {current_desc[:100] if current_desc else '(空)'}...")
            logger.info(f"[OntologyUpdater] 开始为 {table_name} 生成新描述...")

            # 4. AI 生成合并后的描述（传入多实体上下文）
            merge_result = await self._generate_merged_description(
                entity_name=entity_name,
                entity_level=level,
                current_desc=current_desc,
                question=question,
                answer=answer,
                all_entities=all_entities,
                current_entity=table_name,
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
                f"✅ 本体描述已更新 [{level}]: {table_name}\n"
                f"   原描述: {current_desc[:50] if current_desc else '(空)'}...\n"
                f"   新描述: {new_description[:50]}...\n"
                f"   提取信息: {merge_result.get('extracted_info', '')}"
            )

            return {
                "status": "success",
                "entity": table_name,
                "level": level,
                "new_description": new_description,
                "extracted_info": merge_result.get("extracted_info", ""),
                "reasoning": merge_result.get("reasoning", ""),
                "message": update_result,
            }

        except Exception as e:
            logger.error(f"❌ 更新单个实体描述失败 ({table_name}): {e}", exc_info=True)
            return {
                "status": "error",
                "entity": table_name,
                "level": level,
                "message": str(e),
            }
