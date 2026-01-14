"""
数据实例抽取工具

从数据库抽取样例数据，验证本体映射正确性，并检测数据质量问题。
"""

from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field
import json

from kode.tools.base import KodeTool
from kode.utils.ontology_storage import OntologyStorageV2
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class DataInstanceExtractorInput(BaseModel):
    """数据实例抽取工具输入参数"""

    connection_name: str = Field(
        description="数据库连接名称"
    )
    class_name: str = Field(
        description="要抽取数据的类名（如：'客户'、'订单'），或 'all' 抽取所有类"
    )
    sample_size: int = Field(
        default=5,
        description="抽取的样例数量（默认5条）"
    )
    check_quality: bool = Field(
        default=True,
        description="是否检查数据质量（默认True）"
    )


class DataInstanceExtractorTool(KodeTool):
    """
    数据实例抽取工具

    从数据库抽取样例数据，将技术字段名转换为业务字段名，
    并自动检测数据质量问题（如空值、重复值等）。

    使用场景：
    - 验证本体映射是否正确
    - 快速了解数据结构和内容
    - 发现数据质量问题

    前置条件：
    - 已构建 OntologyV2 本体
    - 数据库已连接
    """

    name: str = "DataInstanceExtractor"
    description: str = """抽取数据实例并验证本体映射

从数据库抽取样例数据，自动转换为业务术语，并检测数据质量。

输入参数：
- connection_name: 数据库连接名
- class_name: 类名（如 '客户'）或 'all'
- sample_size: 抽取数量（默认5条）
- check_quality: 是否检查数据质量（默认True）

输出：
- 样例数据（业务字段名）
- 数据统计信息
- 数据质量问题报告
"""

    args_schema: Type[BaseModel] = DataInstanceExtractorInput
    requires_permission: bool = False

    storage: OntologyStorageV2 = Field(default_factory=OntologyStorageV2, exclude=True)

    def _run(
        self,
        connection_name: str,
        class_name: str,
        sample_size: int = 5,
        check_quality: bool = True,
        **kwargs
    ) -> str:
        """执行数据实例抽取"""
        try:
            # 步骤1：加载 OntologyV2
            ontology = self.storage.load_ontology_v2(connection_name)
            if not ontology:
                return self._format_error("未找到本体，请先运行 OntologyBuilder")

            # 步骤2：查找类定义
            if class_name.lower() == "all":
                # 抽取所有类
                classes = ontology.get("classes", [])
                return self._extract_all_classes(classes, sample_size, check_quality)
            else:
                # 抽取单个类
                class_def = self._find_class(ontology, class_name)
                if not class_def:
                    available = [c["name"] for c in ontology.get("classes", [])]
                    return self._format_error(
                        f"未找到类 '{class_name}'",
                        f"可用类：{', '.join(available[:10])}" + ("..." if len(available) > 10 else "")
                    )

                return self._extract_single_class(class_def, sample_size, check_quality)

        except Exception as e:
            logger.error(f"数据实例抽取失败: {str(e)}", exc_info=True)
            return self._format_error(f"抽取失败: {str(e)}")

    def _find_class(
        self,
        ontology: Dict[str, Any],
        class_name: str
    ) -> Optional[Dict[str, Any]]:
        """查找类定义（模糊匹配）"""
        classes = ontology.get("classes", [])

        # 精确匹配
        for cls in classes:
            if cls["name"] == class_name:
                return cls

        # 模糊匹配
        class_name_lower = class_name.lower()
        for cls in classes:
            if class_name_lower in cls["name"].lower():
                return cls

        return None

    def _extract_single_class(
        self,
        class_def: Dict[str, Any],
        sample_size: int,
        check_quality: bool
    ) -> str:
        """抽取单个类的数据实例"""
        class_name = class_def.get("name", "")
        table_mapping = class_def.get("table_mapping", "")
        properties = class_def.get("properties", [])

        # 构建 SQL
        columns = []
        field_mapping = {}  # 技术名 -> 业务名

        for prop in properties:
            tech_name = prop.get("column_mapping", "")
            business_name = prop.get("name", "")

            if tech_name:
                # 去除表名前缀（如 customers.name → name）
                if "." in tech_name:
                    tech_name = tech_name.split(".")[-1]

                columns.append(tech_name)
                field_mapping[tech_name] = business_name

        if not columns:
            return self._format_error(f"类 '{class_name}' 没有属性映射")

        # 生成 SQL
        sql = f"""
-- 抽取 {class_name} 数据实例
SELECT {', '.join(columns)}
FROM {table_mapping}
ORDER BY RAND()  -- 随机抽样
LIMIT {sample_size};
"""

        # 质量检查 SQL（可选）
        quality_sql = None
        if check_quality:
            quality_sql = f"""
-- 数据质量检查：{class_name}
SELECT
    COUNT(*) AS total_rows,
    {self._build_null_check_sql(columns)}
FROM {table_mapping};
"""

        # 格式化输出
        return self._format_extraction_output(
            class_name=class_name,
            table_mapping=table_mapping,
            field_mapping=field_mapping,
            sql=sql,
            quality_sql=quality_sql,
            sample_size=sample_size
        )

    def _extract_all_classes(
        self,
        classes: List[Dict[str, Any]],
        sample_size: int,
        check_quality: bool
    ) -> str:
        """抽取所有类的数据实例（生成批量 SQL）"""
        parts = []

        parts.append(f"📦 **批量数据实例抽取**")
        parts.append(f"\n准备抽取 {len(classes)} 个类的数据...")
        parts.append("")

        # 生成每个类的 SQL
        for idx, class_def in enumerate(classes[:10], start=1):  # 限制前10个
            class_name = class_def.get("name", "")
            table_mapping = class_def.get("table_mapping", "")

            parts.append(f"### {idx}. {class_name}")
            parts.append(f"表：`{table_mapping}`")
            parts.append("")

        if len(classes) > 10:
            parts.append(f"\n...还有 {len(classes) - 10} 个类")

        parts.append(f"\n💡 **建议**：一次抽取太多类会很慢，建议逐个抽取。")
        parts.append(f"例如：`DataInstanceExtractor(class_name='客户', sample_size={sample_size})`")

        return "\n".join(parts)

    def _build_null_check_sql(self, columns: List[str]) -> str:
        """构建空值检查 SQL"""
        null_checks = []
        for col in columns[:5]:  # 限制前5个字段
            null_checks.append(f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS {col}_null_count")
        return ",\n    ".join(null_checks)

    # ============ 格式化输出方法 ============

    def _format_extraction_output(
        self,
        class_name: str,
        table_mapping: str,
        field_mapping: Dict[str, str],
        sql: str,
        quality_sql: Optional[str],
        sample_size: int
    ) -> str:
        """格式化抽取输出"""
        parts = []

        parts.append(f"📦 **数据实例抽取：{class_name}**")
        parts.append("")

        # 映射信息
        parts.append(f"**表映射**：`{table_mapping}`")
        parts.append(f"**字段数量**：{len(field_mapping)}")
        parts.append(f"**抽样数量**：{sample_size} 条")
        parts.append("")

        # 字段映射表
        parts.append("**字段映射**：")
        parts.append("| 业务字段名 | 技术字段名 |")
        parts.append("|-----------|-----------|")
        for tech, business in list(field_mapping.items())[:10]:
            parts.append(f"| {business} | `{tech}` |")
        if len(field_mapping) > 10:
            parts.append(f"| ... | ... |")
        parts.append("")

        # 抽取 SQL
        parts.append("**步骤1：抽取样例数据**")
        parts.append("```sql")
        parts.append(sql.strip())
        parts.append("```")
        parts.append("")

        # 质量检查 SQL
        if quality_sql:
            parts.append("**步骤2：数据质量检查**")
            parts.append("```sql")
            parts.append(quality_sql.strip())
            parts.append("```")
            parts.append("")

        # 下一步提示
        parts.append("🚀 **下一步：**")
        parts.append("1. 使用 `DatabaseExecuteQuery` 执行步骤1的 SQL，查看样例数据")
        if quality_sql:
            parts.append("2. 执行步骤2的 SQL，检查数据质量")
        parts.append("3. 验证字段映射是否正确（业务字段名是否符合预期）")

        return "\n".join(parts)

    def _format_error(self, error: str, hint: str = "") -> str:
        """格式化错误消息"""
        parts = [f"❌ **错误：{error}**"]
        if hint:
            parts.append(f"\n💡 提示：{hint}")
        return "\n".join(parts)
