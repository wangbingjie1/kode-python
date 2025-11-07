"""
可视化工具 - AI 自动生成图表配置
"""

import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from kode.tools.base import KodeTool
from kode.utils.logger import get_logger

logger = get_logger(__name__)


class ChartGeneratorInput(BaseModel):
    """图表生成工具输入"""

    data: str = Field(
        description="查询结果数据，JSON 格式的列表或字典。例如：[{\"month\": \"1月\", \"sales\": 100}, {\"month\": \"2月\", \"sales\": 120}]"
    )
    chart_type: Optional[str] = Field(
        default=None,
        description=(
            "图表类型（可选）。如果不指定，工具会自动选择。"
            "可选值：line（折线图）, bar（柱状图）, pie（饼图）, scatter（散点图）, heatmap（热力图）"
        ),
    )
    x_field: Optional[str] = Field(
        default=None, description="X 轴字段名（用于折线图、柱状图等）"
    )
    y_field: Optional[str] = Field(
        default=None, description="Y 轴字段名（用于折线图、柱状图等）"
    )
    title: Optional[str] = Field(default=None, description="图表标题")


class ChartGeneratorTool(KodeTool):
    """
    图表生成工具 - AI 自动生成 ECharts 配置

    根据数据自动选择合适的可视化类型并生成 ECharts 配置。
    支持折线图、柱状图、饼图、散点图等常见图表类型。
    """

    name: str = "ChartGenerator"
    description: str = (
        "根据查询结果数据自动生成图表配置。"
        "工具会智能选择合适的图表类型（折线图、柱状图、饼图等）并返回 ECharts 配置 JSON。"
        "使用场景：当需要可视化数据时，例如展示趋势、对比、分布等。"
    )
    args_schema: Type[BaseModel] = ChartGeneratorInput
    requires_permission: bool = False

    def _run(
        self,
        data: str,
        chart_type: Optional[str] = None,
        x_field: Optional[str] = None,
        y_field: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """
        生成图表配置

        Args:
            data: JSON 格式的数据
            chart_type: 图表类型（可选，自动推断）
            x_field: X 轴字段
            y_field: Y 轴字段
            title: 图表标题

        Returns:
            包含图表配置的 JSON 字符串
        """
        try:
            # 解析数据
            parsed_data = json.loads(data)

            # 如果数据为空
            if not parsed_data:
                return json.dumps(
                    {
                        "success": False,
                        "error": "数据为空，无法生成图表",
                    },
                    ensure_ascii=False,
                )

            # 自动推断图表类型
            if chart_type is None:
                chart_type = self._infer_chart_type(parsed_data, x_field, y_field)

            # 生成图表配置
            chart_config = self._generate_chart_config(
                parsed_data, chart_type, x_field, y_field, title
            )

            return json.dumps(
                {
                    "success": True,
                    "chart_type": chart_type,
                    "config": chart_config,
                    "data_summary": {
                        "rows": len(parsed_data) if isinstance(parsed_data, list) else 1,
                        "fields": (
                            list(parsed_data[0].keys())
                            if isinstance(parsed_data, list) and parsed_data
                            else list(parsed_data.keys())
                        ),
                    },
                },
                ensure_ascii=False,
            )

        except json.JSONDecodeError as e:
            logger.error(f"数据解析失败: {e}")
            return json.dumps(
                {"success": False, "error": f"数据格式错误: {str(e)}"},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"图表生成失败: {e}")
            return json.dumps(
                {"success": False, "error": f"图表生成失败: {str(e)}"},
                ensure_ascii=False,
            )

    def _infer_chart_type(
        self, data: Any, x_field: Optional[str], y_field: Optional[str]
    ) -> str:
        """
        自动推断图表类型

        Args:
            data: 解析后的数据
            x_field: X 轴字段
            y_field: Y 轴字段

        Returns:
            图表类型
        """
        if not isinstance(data, list) or not data:
            return "bar"

        # 获取第一行数据
        first_row = data[0]
        fields = list(first_row.keys())

        # 如果只有两个字段
        if len(fields) == 2:
            # 检查是否有时间相关字段（用于折线图）
            time_keywords = ["date", "time", "month", "year", "day", "week", "日期", "时间", "月", "年"]
            for field in fields:
                if any(keyword in field.lower() for keyword in time_keywords):
                    return "line"

            # 检查数据量，少于10条用柱状图，多于10条用折线图
            if len(data) <= 10:
                return "bar"
            else:
                return "line"

        # 如果有多个数值字段，使用柱状图
        numeric_fields = [
            f for f in fields if isinstance(first_row.get(f), (int, float))
        ]
        if len(numeric_fields) >= 2:
            return "bar"

        # 默认使用柱状图
        return "bar"

    def _generate_chart_config(
        self,
        data: Any,
        chart_type: str,
        x_field: Optional[str],
        y_field: Optional[str],
        title: Optional[str],
    ) -> Dict[str, Any]:
        """
        生成 ECharts 配置

        Args:
            data: 解析后的数据
            chart_type: 图表类型
            x_field: X 轴字段
            y_field: Y 轴字段
            title: 图表标题

        Returns:
            ECharts 配置字典
        """
        if chart_type == "line":
            return self._generate_line_chart(data, x_field, y_field, title)
        elif chart_type == "bar":
            return self._generate_bar_chart(data, x_field, y_field, title)
        elif chart_type == "pie":
            return self._generate_pie_chart(data, x_field, y_field, title)
        elif chart_type == "scatter":
            return self._generate_scatter_chart(data, x_field, y_field, title)
        else:
            # 默认柱状图
            return self._generate_bar_chart(data, x_field, y_field, title)

    def _auto_detect_fields(
        self, data: List[Dict[str, Any]], x_field: Optional[str], y_field: Optional[str]
    ) -> tuple[str, str]:
        """
        自动检测 X 和 Y 字段

        Args:
            data: 数据列表
            x_field: 指定的 X 字段
            y_field: 指定的 Y 字段

        Returns:
            (x_field, y_field) 元组
        """
        if not data:
            return x_field or "x", y_field or "y"

        fields = list(data[0].keys())

        # 如果已指定，直接返回
        if x_field and y_field:
            return x_field, y_field

        # 自动检测
        numeric_fields = [
            f for f in fields if isinstance(data[0].get(f), (int, float))
        ]
        text_fields = [f for f in fields if isinstance(data[0].get(f), str)]

        # X 轴通常是文本或时间
        if not x_field:
            x_field = text_fields[0] if text_fields else fields[0]

        # Y 轴通常是数值
        if not y_field:
            y_field = numeric_fields[0] if numeric_fields else fields[-1]

        return x_field, y_field

    def _generate_line_chart(
        self,
        data: List[Dict[str, Any]],
        x_field: Optional[str],
        y_field: Optional[str],
        title: Optional[str],
    ) -> Dict[str, Any]:
        """生成折线图配置"""
        x_field, y_field = self._auto_detect_fields(data, x_field, y_field)

        x_data = [row.get(x_field, "") for row in data]
        y_data = [row.get(y_field, 0) for row in data]

        return {
            "title": {"text": title or "数据趋势", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "name": x_field},
            "yAxis": {"type": "value", "name": y_field},
            "series": [
                {
                    "name": y_field,
                    "type": "line",
                    "data": y_data,
                    "smooth": True,
                    "lineStyle": {"width": 3},
                    "itemStyle": {"borderWidth": 2},
                }
            ],
            "grid": {"left": "10%", "right": "10%", "bottom": "15%", "top": "15%"},
        }

    def _generate_bar_chart(
        self,
        data: List[Dict[str, Any]],
        x_field: Optional[str],
        y_field: Optional[str],
        title: Optional[str],
    ) -> Dict[str, Any]:
        """生成柱状图配置"""
        x_field, y_field = self._auto_detect_fields(data, x_field, y_field)

        x_data = [row.get(x_field, "") for row in data]
        y_data = [row.get(y_field, 0) for row in data]

        return {
            "title": {"text": title or "数据对比", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "name": x_field},
            "yAxis": {"type": "value", "name": y_field},
            "series": [
                {
                    "name": y_field,
                    "type": "bar",
                    "data": y_data,
                    "itemStyle": {"borderRadius": [4, 4, 0, 0]},
                }
            ],
            "grid": {"left": "10%", "right": "10%", "bottom": "15%", "top": "15%"},
        }

    def _generate_pie_chart(
        self,
        data: List[Dict[str, Any]],
        x_field: Optional[str],
        y_field: Optional[str],
        title: Optional[str],
    ) -> Dict[str, Any]:
        """生成饼图配置"""
        x_field, y_field = self._auto_detect_fields(data, x_field, y_field)

        pie_data = [
            {"name": row.get(x_field, ""), "value": row.get(y_field, 0)} for row in data
        ]

        return {
            "title": {"text": title or "数据分布", "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [
                {
                    "name": y_field,
                    "type": "pie",
                    "radius": "60%",
                    "data": pie_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)",
                        }
                    },
                }
            ],
        }

    def _generate_scatter_chart(
        self,
        data: List[Dict[str, Any]],
        x_field: Optional[str],
        y_field: Optional[str],
        title: Optional[str],
    ) -> Dict[str, Any]:
        """生成散点图配置"""
        x_field, y_field = self._auto_detect_fields(data, x_field, y_field)

        scatter_data = [
            [row.get(x_field, 0), row.get(y_field, 0)] for row in data
        ]

        return {
            "title": {"text": title or "数据分布", "left": "center"},
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": x_field},
            "yAxis": {"type": "value", "name": y_field},
            "series": [
                {
                    "name": f"{x_field} vs {y_field}",
                    "type": "scatter",
                    "data": scatter_data,
                    "symbolSize": 10,
                }
            ],
            "grid": {"left": "10%", "right": "10%", "bottom": "15%", "top": "15%"},
        }
