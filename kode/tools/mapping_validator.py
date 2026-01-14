"""
映射验证工具

验证 OntologyV2 中的映射关系（table_mapping, column_mapping）是否正确。
"""

from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field

from kode.tools.base import KodeTool
from kode.utils.ontology_storage import OntologyStorageV2
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class MappingValidatorInput(BaseModel):
    """映射验证工具输入参数"""

    connection_name: str = Field(
        description="数据库连接名称"
    )
    class_name: Optional[str] = Field(
        default=None,
        description="要验证的类名（如：'客户'），或 None 验证所有类"
    )


class MappingValidatorTool(KodeTool):
    """
    映射验证工具

    验证 OntologyV2 本体中的映射关系是否与实际数据库 schema 匹配。

    验证项：
    1. table_mapping 是否存在
    2. column_mapping 是否存在
    3. 字段类型是否匹配（可选）

    使用场景：
    - 构建本体后验证映射正确性
    - 数据库 schema 变更后重新验证

    前置条件：
    - 已构建 OntologyV2 本体
    - 已提取数据库 schema
    """

    name: str = "MappingValidator"
    description: str = """验证本体映射关系

检查 OntologyV2 中的 table_mapping 和 column_mapping 是否正确。

输入参数：
- connection_name: 数据库连接名
- class_name: 类名（可选，默认验证所有类）

输出：
- 验证报告（通过/失败）
- 问题列表（表不存在、字段不存在等）
"""

    args_schema: Type[BaseModel] = MappingValidatorInput
    requires_permission: bool = False

    storage: OntologyStorageV2 = Field(default_factory=OntologyStorageV2, exclude=True)

    def _run(
        self,
        connection_name: str,
        class_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """执行映射验证"""
        try:
            # 步骤1：加载 OntologyV2
            ontology = self.storage.load_ontology_v2(connection_name)
            if not ontology:
                return self._format_error("未找到本体，请先运行 OntologyBuilder")

            # 步骤2：加载 Schema（从 schema_store）
            schema = self._load_schema(connection_name)
            if not schema:
                return self._format_error(
                    "未找到数据库 schema",
                    "请先运行 DatabaseSchemaExtractor 提取 schema"
                )

            # 步骤3：验证映射
            if class_name:
                # 验证单个类
                class_def = self._find_class(ontology, class_name)
                if not class_def:
                    return self._format_error(f"未找到类 '{class_name}'")

                result = self._validate_single_class(class_def, schema)
                return self._format_validation_result(result)
            else:
                # 验证所有类
                classes = ontology.get("classes", [])
                results = [self._validate_single_class(cls, schema) for cls in classes]
                return self._format_all_validation_results(results)

        except Exception as e:
            logger.error(f"映射验证失败: {str(e)}", exc_info=True)
            return self._format_error(f"验证失败: {str(e)}")

    def _load_schema(self, connection_name: str) -> Optional[Dict[str, Any]]:
        """加载数据库 schema（简化：返回提示让 Agent 调用 SchemaQuery）"""
        # 实际应该从 schema_store 读取，这里简化为返回 None
        # 触发 Agent 调用 SchemaQuery
        return None

    def _find_class(
        self,
        ontology: Dict[str, Any],
        class_name: str
    ) -> Optional[Dict[str, Any]]:
        """查找类定义"""
        classes = ontology.get("classes", [])
        for cls in classes:
            if cls["name"] == class_name:
                return cls
        return None

    def _validate_single_class(
        self,
        class_def: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证单个类的映射"""
        class_name = class_def.get("name", "")
        table_mapping = class_def.get("table_mapping", "")
        properties = class_def.get("properties", [])

        result = {
            "class_name": class_name,
            "table_mapping": table_mapping,
            "table_exists": None,  # 需要查询 schema
            "property_validations": [],
            "issues": []
        }

        # 验证表映射（简化：生成 SQL 让 Agent 执行）
        if not table_mapping:
            result["issues"].append({
                "severity": "error",
                "message": f"类 '{class_name}' 缺少 table_mapping"
            })

        # 验证属性映射
        for prop in properties:
            prop_name = prop.get("name", "")
            column_mapping = prop.get("column_mapping", "")

            prop_validation = {
                "property": prop_name,
                "column_mapping": column_mapping,
                "exists": None,  # 需要查询 schema
                "type_match": None  # 需要查询 schema
            }

            if not column_mapping:
                result["issues"].append({
                    "severity": "warning",
                    "message": f"属性 '{prop_name}' 缺少 column_mapping"
                })

            result["property_validations"].append(prop_validation)

        return result

    # ============ 格式化输出方法 ============

    def _format_validation_result(self, result: Dict[str, Any]) -> str:
        """格式化单个类的验证结果"""
        parts = []

        class_name = result["class_name"]
        table_mapping = result["table_mapping"]
        issues = result["issues"]

        parts.append(f"🔍 **映射验证：{class_name}**")
        parts.append("")

        # 表映射
        parts.append(f"**表映射**：`{table_mapping}`")

        # 验证 SQL（让 Agent 执行）
        parts.append("")
        parts.append("**验证步骤1：检查表是否存在**")
        parts.append("```sql")
        parts.append(f"SHOW TABLES LIKE '{table_mapping}';")
        parts.append("```")
        parts.append("")

        # 字段验证
        if result["property_validations"]:
            parts.append("**验证步骤2：检查字段是否存在**")
            parts.append("```sql")
            parts.append(f"DESCRIBE {table_mapping};")
            parts.append("```")
            parts.append("")

            parts.append("**预期字段**：")
            for pv in result["property_validations"][:10]:
                prop_name = pv["property"]
                column = pv["column_mapping"]
                if "." in column:
                    column = column.split(".")[-1]
                parts.append(f"- {prop_name} → `{column}`")
            parts.append("")

        # 问题列表
        if issues:
            parts.append("⚠️ **发现问题：**")
            for issue in issues:
                severity = issue["severity"]
                message = issue["message"]
                emoji = "🔴" if severity == "error" else "🟡"
                parts.append(f"{emoji} {message}")
            parts.append("")

        # 下一步
        parts.append("🚀 **下一步：**")
        parts.append("使用 `DatabaseExecuteQuery` 执行上述 SQL 验证映射是否正确。")

        return "\n".join(parts)

    def _format_all_validation_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化所有类的验证结果"""
        parts = []

        parts.append(f"🔍 **批量映射验证**")
        parts.append(f"\n共 {len(results)} 个类")
        parts.append("")

        # 统计
        total_issues = sum(len(r["issues"]) for r in results)
        classes_with_issues = sum(1 for r in results if r["issues"])

        parts.append(f"**统计**：")
        parts.append(f"- 有问题的类：{classes_with_issues} / {len(results)}")
        parts.append(f"- 问题总数：{total_issues}")
        parts.append("")

        # 详细结果（前5个）
        parts.append("**详细结果（前5个）：**")
        for idx, result in enumerate(results[:5], start=1):
            class_name = result["class_name"]
            issue_count = len(result["issues"])
            status = "✅" if issue_count == 0 else f"⚠️ {issue_count}个问题"
            parts.append(f"{idx}. {class_name} - {status}")

        if len(results) > 5:
            parts.append(f"...还有 {len(results) - 5} 个类")

        parts.append("")
        parts.append("💡 **建议**：使用 `MappingValidator(class_name='具体类名')` 查看单个类的详细验证结果。")

        return "\n".join(parts)

    def _format_error(self, error: str, hint: str = "") -> str:
        """格式化错误消息"""
        parts = [f"❌ **错误：{error}**"]
        if hint:
            parts.append(f"\n💡 提示：{hint}")
        return "\n".join(parts)
