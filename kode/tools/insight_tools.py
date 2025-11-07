"""
洞察提取工具 - AI 自动发现数据中的关键信息
"""

import json
import statistics
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from kode.tools.base import KodeTool
from kode.utils.logger import get_logger

logger = get_logger(__name__)


class InsightExtractorInput(BaseModel):
    """洞察提取工具输入"""

    data: str = Field(
        description="查询结果数据，JSON 格式的列表或字典。例如：[{\"month\": \"1月\", \"sales\": 100}, {\"month\": \"2月\", \"sales\": 120}]"
    )
    value_field: Optional[str] = Field(
        default=None, description="要分析的数值字段名（如果不指定，自动检测）"
    )
    context: Optional[str] = Field(
        default=None, description="业务上下文信息，帮助生成更准确的洞察"
    )


class InsightExtractorTool(KodeTool):
    """
    洞察提取工具 - 自动发现数据中的趋势、异常和关键信息

    分析数据并提取以下类型的洞察：
    1. 趋势洞察：数据的增长或下降趋势
    2. 异常洞察：明显偏离正常范围的数据点
    3. 对比洞察：最大值、最小值、平均值等关键统计信息
    4. 占比洞察：主要贡献者的占比情况
    """

    name: str = "InsightExtractor"
    description: str = (
        "从数据中自动提取关键洞察，包括趋势、异常、对比和占比等信息。"
        "使用场景：当需要快速理解数据特征、发现异常模式或关键指标时。"
    )
    args_schema: Type[BaseModel] = InsightExtractorInput
    requires_permission: bool = False

    def _run(
        self,
        data: str,
        value_field: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        提取洞察

        Args:
            data: JSON 格式的数据
            value_field: 要分析的数值字段
            context: 业务上下文

        Returns:
            包含洞察列表的 JSON 字符串
        """
        try:
            # 解析数据
            parsed_data = json.loads(data)

            # 如果数据为空
            if not parsed_data:
                return json.dumps(
                    {"success": False, "error": "数据为空，无法提取洞察"},
                    ensure_ascii=False,
                )

            # 确保数据是列表格式
            if not isinstance(parsed_data, list):
                parsed_data = [parsed_data]

            # 自动检测数值字段
            if value_field is None:
                value_field = self._detect_value_field(parsed_data)

            # 提取各类洞察
            insights = []

            # 1. 趋势洞察
            trend_insights = self._extract_trend_insights(parsed_data, value_field)
            insights.extend(trend_insights)

            # 2. 异常洞察
            anomaly_insights = self._extract_anomaly_insights(parsed_data, value_field)
            insights.extend(anomaly_insights)

            # 3. 对比洞察
            comparison_insights = self._extract_comparison_insights(
                parsed_data, value_field
            )
            insights.extend(comparison_insights)

            # 4. 占比洞察（如果数据适合）
            if len(parsed_data) >= 3:
                proportion_insights = self._extract_proportion_insights(
                    parsed_data, value_field
                )
                insights.extend(proportion_insights)

            return json.dumps(
                {
                    "success": True,
                    "insights": insights,
                    "total_count": len(insights),
                    "data_summary": {
                        "rows": len(parsed_data),
                        "analyzed_field": value_field,
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
            logger.error(f"洞察提取失败: {e}")
            return json.dumps(
                {"success": False, "error": f"洞察提取失败: {str(e)}"},
                ensure_ascii=False,
            )

    def _detect_value_field(self, data: List[Dict[str, Any]]) -> str:
        """
        自动检测数值字段

        Args:
            data: 数据列表

        Returns:
            数值字段名
        """
        if not data:
            return "value"

        first_row = data[0]
        numeric_fields = [
            field
            for field, value in first_row.items()
            if isinstance(value, (int, float))
        ]

        # 优先选择包含特定关键词的字段
        priority_keywords = ["销售", "金额", "数量", "amount", "sales", "count", "value"]
        for field in numeric_fields:
            if any(keyword in field.lower() for keyword in priority_keywords):
                return field

        # 否则返回第一个数值字段
        return numeric_fields[0] if numeric_fields else "value"

    def _get_label_field(self, data: List[Dict[str, Any]], value_field: str) -> str:
        """
        获取标签字段（非数值字段）

        Args:
            data: 数据列表
            value_field: 数值字段名

        Returns:
            标签字段名
        """
        if not data:
            return "label"

        first_row = data[0]
        text_fields = [
            field for field, value in first_row.items() if isinstance(value, str)
        ]

        return text_fields[0] if text_fields else "label"

    def _extract_trend_insights(
        self, data: List[Dict[str, Any]], value_field: str
    ) -> List[Dict[str, Any]]:
        """提取趋势洞察"""
        insights = []

        if len(data) < 3:
            return insights

        # 提取数值序列
        values = [row.get(value_field, 0) for row in data if value_field in row]

        if len(values) < 3:
            return insights

        # 计算整体趋势
        first_half_avg = statistics.mean(values[: len(values) // 2])
        second_half_avg = statistics.mean(values[len(values) // 2 :])

        if first_half_avg > 0:
            change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

            if abs(change_percent) > 5:  # 变化超过 5% 才认为是明显趋势
                trend_type = "上升" if change_percent > 0 else "下降"
                insights.append(
                    {
                        "type": "trend",
                        "severity": "high" if abs(change_percent) > 20 else "medium",
                        "content": f"数据呈现{trend_type}趋势，变化幅度约 {abs(change_percent):.1f}%",
                        "icon": "📈" if change_percent > 0 else "📉",
                        "metadata": {
                            "change_percent": round(change_percent, 2),
                            "first_half_avg": round(first_half_avg, 2),
                            "second_half_avg": round(second_half_avg, 2),
                        },
                    }
                )

        return insights

    def _extract_anomaly_insights(
        self, data: List[Dict[str, Any]], value_field: str
    ) -> List[Dict[str, Any]]:
        """提取异常洞察"""
        insights = []

        if len(data) < 5:
            return insights

        # 提取数值
        values = [row.get(value_field, 0) for row in data if value_field in row]

        if len(values) < 5:
            return insights

        # 计算统计指标
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) > 1 else 0

        if stdev_val == 0:
            return insights

        # 使用 Z-score 检测异常（|Z| > 2 认为是异常）
        label_field = self._get_label_field(data, value_field)

        for idx, row in enumerate(data):
            value = row.get(value_field, 0)
            z_score = (value - mean_val) / stdev_val if stdev_val > 0 else 0

            if abs(z_score) > 2:
                label = row.get(label_field, f"数据点{idx + 1}")
                deviation_percent = ((value - mean_val) / mean_val) * 100

                insights.append(
                    {
                        "type": "anomaly",
                        "severity": "high" if abs(z_score) > 3 else "medium",
                        "content": f"{label} 出现异常，数值为 {value:.2f}，偏离平均值 {abs(deviation_percent):.1f}%",
                        "icon": "⚠️",
                        "metadata": {
                            "label": label,
                            "value": round(value, 2),
                            "mean": round(mean_val, 2),
                            "z_score": round(z_score, 2),
                            "deviation_percent": round(deviation_percent, 2),
                        },
                    }
                )

        return insights

    def _extract_comparison_insights(
        self, data: List[Dict[str, Any]], value_field: str
    ) -> List[Dict[str, Any]]:
        """提取对比洞察"""
        insights = []

        # 提取数值
        values = [row.get(value_field, 0) for row in data if value_field in row]

        if not values:
            return insights

        # 计算统计指标
        max_val = max(values)
        min_val = min(values)
        avg_val = statistics.mean(values)

        # 找到最大值和最小值对应的标签
        label_field = self._get_label_field(data, value_field)

        max_row = max(data, key=lambda x: x.get(value_field, 0))
        min_row = min(data, key=lambda x: x.get(value_field, 0))

        max_label = max_row.get(label_field, "")
        min_label = min_row.get(label_field, "")

        # 最大值洞察
        if max_label:
            insights.append(
                {
                    "type": "comparison",
                    "severity": "medium",
                    "content": f"{max_label} 数值最高，为 {max_val:.2f}",
                    "icon": "🏆",
                    "metadata": {"label": max_label, "value": round(max_val, 2)},
                }
            )

        # 最小值洞察
        if min_label and max_val > 0:
            gap_percent = ((max_val - min_val) / max_val) * 100
            insights.append(
                {
                    "type": "comparison",
                    "severity": "low",
                    "content": f"{min_label} 数值最低，为 {min_val:.2f}，与最高值相差 {gap_percent:.1f}%",
                    "icon": "📊",
                    "metadata": {
                        "label": min_label,
                        "value": round(min_val, 2),
                        "gap_percent": round(gap_percent, 2),
                    },
                }
            )

        # 平均值洞察
        if len(values) >= 3:
            insights.append(
                {
                    "type": "comparison",
                    "severity": "low",
                    "content": f"平均值为 {avg_val:.2f}",
                    "icon": "📍",
                    "metadata": {"average": round(avg_val, 2), "count": len(values)},
                }
            )

        return insights

    def _extract_proportion_insights(
        self, data: List[Dict[str, Any]], value_field: str
    ) -> List[Dict[str, Any]]:
        """提取占比洞察"""
        insights = []

        # 计算总和
        total = sum(row.get(value_field, 0) for row in data)

        if total == 0:
            return insights

        # 找到占比最大的项
        label_field = self._get_label_field(data, value_field)

        top_row = max(data, key=lambda x: x.get(value_field, 0))
        top_value = top_row.get(value_field, 0)
        top_label = top_row.get(label_field, "")
        top_percent = (top_value / total) * 100

        if top_percent > 30:  # 占比超过 30% 才提示
            insights.append(
                {
                    "type": "proportion",
                    "severity": "medium",
                    "content": f"{top_label} 占比最高，达到 {top_percent:.1f}%",
                    "icon": "📊",
                    "metadata": {
                        "label": top_label,
                        "value": round(top_value, 2),
                        "percent": round(top_percent, 2),
                        "total": round(total, 2),
                    },
                }
            )

        # 检查是否有集中度过高的情况（前3名占比超过80%）
        if len(data) >= 5:
            sorted_data = sorted(data, key=lambda x: x.get(value_field, 0), reverse=True)
            top3_sum = sum(row.get(value_field, 0) for row in sorted_data[:3])
            top3_percent = (top3_sum / total) * 100

            if top3_percent > 80:
                insights.append(
                    {
                        "type": "proportion",
                        "severity": "medium",
                        "content": f"前3名占比达 {top3_percent:.1f}%，数据集中度较高",
                        "icon": "🎯",
                        "metadata": {"top3_percent": round(top3_percent, 2)},
                    }
                )

        return insights
