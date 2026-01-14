"""
指标计算工具

从 OntologyV2 读取指标定义，转换为可执行的 SQL 并计算结果。
"""

from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json

from kode.tools.base import KodeTool
from kode.utils.ontology_storage import OntologyStorageV2
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class MetricCalculatorInput(BaseModel):
    """指标计算工具输入参数"""

    connection_name: str = Field(
        description="数据库连接名称"
    )
    metric_name: str = Field(
        description="要计算的指标名称（如：'MRR'、'Churn Rate'）"
    )
    time_range: Optional[str] = Field(
        default=None,
        description="时间范围（可选）：'last_7_days', 'last_month', 'last_quarter', 'last_year', 'all_time'"
    )
    group_by: Optional[str] = Field(
        default=None,
        description="分组维度（可选）：'day', 'week', 'month', 'year'"
    )


class MetricCalculatorTool(KodeTool):
    """
    指标计算工具

    从 OntologyV2 本体中读取指标定义，将业务公式转换为可执行的 SQL，
    并调用 DatabaseExecuteQuery 执行计算。

    使用场景：
    - 计算业务指标（MRR、Churn Rate、LTV 等）
    - 生成时间序列数据（按天/周/月分组）
    - 自动生成可视化配置

    前置条件：
    - 已构建 OntologyV2 本体
    - 指标已在 ontology_v2.json 的 metrics 中定义
    """

    name: str = "MetricCalculator"
    description: str = """计算业务指标

从本体中读取指标定义，自动生成 SQL 并执行计算。

输入参数：
- connection_name: 数据库连接名
- metric_name: 指标名称（如 'MRR'、'Churn Rate'）
- time_range: 时间范围（可选，如 'last_month'）
- group_by: 分组维度（可选，如 'day'、'month'）

输出：
- 指标值（单个值或时间序列）
- 生成的 SQL
- 可选的图表配置
"""

    args_schema: Type[BaseModel] = MetricCalculatorInput
    requires_permission: bool = False

    storage: OntologyStorageV2 = Field(default_factory=OntologyStorageV2, exclude=True)

    def _run(
        self,
        connection_name: str,
        metric_name: str,
        time_range: Optional[str] = None,
        group_by: Optional[str] = None,
        **kwargs
    ) -> str:
        """执行指标计算"""
        try:
            # 步骤1：加载 OntologyV2
            ontology = self.storage.load_ontology_v2(connection_name)
            if not ontology:
                return self._format_error("未找到本体，请先运行 OntologyBuilder")

            # 步骤2：查找指标定义
            metric_def = self._find_metric(ontology, metric_name)
            if not metric_def:
                available = [m["name"] for m in ontology.get("metrics", [])]
                return self._format_error(
                    f"未找到指标 '{metric_name}'",
                    f"可用指标：{', '.join(available)}"
                )

            # 步骤3：构建 SQL
            sql = self._build_sql(
                metric_def=metric_def,
                ontology=ontology,
                time_range=time_range,
                group_by=group_by
            )

            # 步骤4：返回 SQL（让 Agent 调用 DatabaseExecuteQuery 执行）
            return self._format_sql_output(
                metric_name=metric_name,
                metric_def=metric_def,
                sql=sql,
                time_range=time_range,
                group_by=group_by
            )

        except Exception as e:
            logger.error(f"指标计算失败: {str(e)}", exc_info=True)
            return self._format_error(f"计算失败: {str(e)}")

    def _find_metric(
        self,
        ontology: Dict[str, Any],
        metric_name: str
    ) -> Optional[Dict[str, Any]]:
        """查找指标定义（模糊匹配）"""
        metrics = ontology.get("metrics", [])

        # 精确匹配
        for metric in metrics:
            if metric["name"] == metric_name:
                return metric

        # 模糊匹配（忽略大小写）
        metric_name_lower = metric_name.lower()
        for metric in metrics:
            if metric_name_lower in metric["name"].lower():
                return metric

        return None

    def _build_sql(
        self,
        metric_def: Dict[str, Any],
        ontology: Dict[str, Any],
        time_range: Optional[str],
        group_by: Optional[str]
    ) -> str:
        """构建 SQL 查询"""
        formula = metric_def.get("formula", "")
        dependencies = metric_def.get("dependencies", [])

        # 查找依赖的 classes
        classes = ontology.get("classes", [])
        dep_classes = {
            cls["name"]: cls
            for cls in classes
            if cls["name"] in dependencies
        }

        # 生成 SQL（简化版，基于公式模式识别）
        sql = self._generate_sql_from_formula(
            formula=formula,
            dep_classes=dep_classes,
            time_range=time_range,
            group_by=group_by
        )

        return sql

    def _generate_sql_from_formula(
        self,
        formula: str,
        dep_classes: Dict[str, Dict],
        time_range: Optional[str],
        group_by: Optional[str]
    ) -> str:
        """从公式生成 SQL（模式识别）"""

        # 模式1：SUM(表.字段) 或 COUNT(...)
        if "SUM" in formula or "COUNT" in formula:
            # 提取主表
            main_table = self._extract_main_table(formula, dep_classes)
            if not main_table:
                # 使用第一个依赖类
                if dep_classes:
                    main_table = list(dep_classes.values())[0]

            if not main_table:
                return f"-- 无法生成 SQL：{formula}"

            table_name = main_table.get("table_mapping", "unknown")

            # 构建基本 SELECT
            select_parts = []
            if "SUM" in formula:
                # 尝试提取字段名
                amount_field = self._find_amount_field(main_table)
                if group_by:
                    select_parts.append(self._get_group_by_field(group_by))
                    select_parts.append(f"SUM({amount_field}) AS total")
                else:
                    select_parts.append(f"SUM({amount_field}) AS total")
            elif "COUNT" in formula:
                if group_by:
                    select_parts.append(self._get_group_by_field(group_by))
                    select_parts.append("COUNT(*) AS count")
                else:
                    select_parts.append("COUNT(*) AS count")

            sql = f"SELECT {', '.join(select_parts)}\nFROM {table_name}"

            # 添加 WHERE 条件
            where_clauses = []

            # 时间范围
            if time_range:
                time_clause = self._get_time_clause(time_range, main_table)
                if time_clause:
                    where_clauses.append(time_clause)

            # 公式中的过滤条件（如 WHERE type='订阅'）
            if "WHERE" in formula:
                filter_condition = self._extract_filter_from_formula(formula, main_table)
                if filter_condition:
                    where_clauses.append(filter_condition)

            if where_clauses:
                sql += "\nWHERE " + " AND ".join(where_clauses)

            # 分组
            if group_by:
                sql += f"\nGROUP BY {self._get_group_by_field(group_by)}"
                sql += f"\nORDER BY {self._get_group_by_field(group_by)}"

            return sql

        # 模式2：计算公式（如 A / B）
        elif "/" in formula or "×" in formula or "*" in formula:
            # 复杂计算，返回公式说明
            return f"-- 复杂计算公式需要多步 SQL：{formula}\n-- 建议拆分为多个指标分别计算"

        else:
            # 未识别的模式
            return f"-- 无法自动生成 SQL：{formula}"

    def _extract_main_table(
        self,
        formula: str,
        dep_classes: Dict[str, Dict]
    ) -> Optional[Dict[str, Any]]:
        """从公式中提取主表"""
        # 简化：查找公式中出现的类名
        for class_name, class_def in dep_classes.items():
            if class_name in formula:
                return class_def
        return None

    def _find_amount_field(self, table_def: Dict[str, Any]) -> str:
        """查找金额字段"""
        properties = table_def.get("properties", [])

        # 优先查找名称包含"金额"、"amount"的字段
        for prop in properties:
            prop_name = prop.get("name", "").lower()
            if "金额" in prop_name or "amount" in prop_name:
                return prop.get("column_mapping", "amount")

        # 默认返回 amount
        return "amount"

    def _get_time_clause(
        self,
        time_range: str,
        table_def: Dict[str, Any]
    ) -> Optional[str]:
        """生成时间过滤条件"""
        # 查找时间字段
        time_field = self._find_time_field(table_def)
        if not time_field:
            return None

        # 根据时间范围生成条件
        time_conditions = {
            "last_7_days": f"{time_field} >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)",
            "last_month": f"{time_field} >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
            "last_quarter": f"{time_field} >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)",
            "last_year": f"{time_field} >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)",
        }

        return time_conditions.get(time_range)

    def _find_time_field(self, table_def: Dict[str, Any]) -> Optional[str]:
        """查找时间字段"""
        properties = table_def.get("properties", [])

        # 查找包含"时间"、"date"、"created"的字段
        for prop in properties:
            prop_name = prop.get("name", "").lower()
            if any(kw in prop_name for kw in ["时间", "date", "created", "日期"]):
                return prop.get("column_mapping", "created_at")

        return None

    def _get_group_by_field(self, group_by: str) -> str:
        """生成分组字段"""
        if group_by == "day":
            return "DATE(created_at) AS date"
        elif group_by == "week":
            return "DATE_FORMAT(created_at, '%Y-%u') AS week"
        elif group_by == "month":
            return "DATE_FORMAT(created_at, '%Y-%m') AS month"
        elif group_by == "year":
            return "YEAR(created_at) AS year"
        else:
            return "created_at"

    def _extract_filter_from_formula(
        self,
        formula: str,
        table_def: Dict[str, Any]
    ) -> Optional[str]:
        """从公式中提取过滤条件"""
        # 简化：查找 WHERE 后的内容
        if "WHERE" in formula:
            parts = formula.split("WHERE")
            if len(parts) > 1:
                filter_part = parts[1].strip()
                # 转换业务字段名为技术字段名
                return self._convert_business_to_tech_names(filter_part, table_def)
        return None

    def _convert_business_to_tech_names(
        self,
        condition: str,
        table_def: Dict[str, Any]
    ) -> str:
        """将业务字段名转换为技术字段名"""
        # 简化：直接返回（完整实现需要解析条件并替换字段名）
        # 例如："订单.类型 = '订阅'" → "type = 'subscription'"
        return condition

    # ============ 格式化输出方法 ============

    def _format_sql_output(
        self,
        metric_name: str,
        metric_def: Dict[str, Any],
        sql: str,
        time_range: Optional[str],
        group_by: Optional[str]
    ) -> str:
        """格式化 SQL 输出"""
        parts = []

        parts.append(f"📊 **指标计算：{metric_name}**")
        parts.append("")

        # 指标说明
        parts.append(f"**描述**：{metric_def.get('description', '')}")
        parts.append(f"**公式**：{metric_def.get('formula', '')}")

        if time_range:
            parts.append(f"**时间范围**：{time_range}")
        if group_by:
            parts.append(f"**分组**：{group_by}")

        parts.append("")

        # 生成的 SQL
        parts.append("**生成的 SQL：**")
        parts.append("```sql")
        parts.append(sql)
        parts.append("```")
        parts.append("")

        # 下一步提示
        parts.append("🚀 **下一步：**")
        parts.append("请使用 `DatabaseExecuteQuery` 执行上述 SQL，我会自动生成图表展示结果。")

        return "\n".join(parts)

    def _format_error(self, error: str, hint: str = "") -> str:
        """格式化错误消息"""
        parts = [f"❌ **错误：{error}**"]
        if hint:
            parts.append(f"\n💡 提示：{hint}")
        return "\n".join(parts)
