"""Domain-based parallel uncertainty analysis for schema clustering."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from kode.core.model_manager import ModelManager
from kode.tools.base import KodeTool
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class DomainUncertaintyAnalyzerInput(BaseModel):
    """Input schema for DomainUncertaintyAnalyzer."""

    connection_name: str = Field(description="Database connection name")
    llm_model: str = Field(default="main", description="LLM model to use (main/task/quick)")
    max_concurrent_domains: int = Field(
        default=5,
        description="Maximum concurrent domain analyses (to avoid API rate limits)"
    )


class DomainUncertaintyAnalyzer(KodeTool):
    """
    并行分析多个域的不确定性（uncertainties），合并后按优先级分类。

    这个工具会：
    1. 并行加载所有域的 schema
    2. 并行调用 AI 分析每个域的不确定性
    3. 合并所有域的 uncertainties
    4. 按优先级（high/medium/low）分组
    5. 返回分级的问题列表，供用户依次回答

    **重要**：这个工具只负责收集问题，不构建本体。
    用户必须先回答所有 high 优先级问题，才能继续构建本体。
    """

    name: str = "DomainUncertaintyAnalyzer"
    description: str = """Parallel analysis of uncertainties across all schema domains.

    Analyzes each domain in parallel to identify:
    - Schema ambiguities
    - Missing constraints
    - Naming confusions
    - Business logic gaps
    - Data quality concerns

    Returns uncertainties grouped by priority (high/medium/low) for user clarification.
    """

    args_schema: Type[BaseModel] = DomainUncertaintyAnalyzerInput
    requires_permission: bool = False

    def _run(
        self,
        connection_name: str,
        llm_model: str = "main",
        max_concurrent_domains: int = 5
    ) -> str:
        """并行分析所有域的不确定性"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        try:
            # 加载配置和域索引
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")
            domain_index_file = Path(schema_path) / connection_name / "domain_index.json"

            if not domain_index_file.exists():
                raise FileNotFoundError(f"Domain index not found: {domain_index_file}")

            with open(domain_index_file, "r", encoding="utf-8") as f:
                domains = json.load(f).get("domains", [])

            if not domains:
                raise ValueError("No domains found")

            # 初始化模型
            model_manager = ModelManager(config.get_all())
            model = model_manager.get_model(llm_model)
            model.temperature = 0.0
            model.max_tokens = 16000

            # 单域分析函数
            def analyze_domain(domain: Dict[str, Any]) -> Dict[str, Any]:
                domain_name = domain["name"]
                domain_file = Path(schema_path) / connection_name / domain["file_path"]

                logger.info(f"分析域: {domain_name} ({domain['table_count']} 个表)")

                with open(domain_file, "r", encoding="utf-8") as f:
                    domain_schema = json.load(f)

                uncertainties = self._analyze_domain(domain_name, domain_schema, model)

                logger.info(f"域 {domain_name}: 识别到 {len(uncertainties)} 个不确定性")

                return {
                    "domain_name": domain_name,
                    "table_count": domain["table_count"],
                    "uncertainty_count": len(uncertainties),
                    "uncertainties": uncertainties
                }

            # 线程池并行执行
            all_uncertainties = []
            domain_results = []

            with ThreadPoolExecutor(max_workers=max_concurrent_domains) as executor:
                futures = {executor.submit(analyze_domain, d): d for d in domains}

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        all_uncertainties.extend(result["uncertainties"])
                        domain_results.append({
                            "domain_name": result["domain_name"],
                            "table_count": result["table_count"],
                            "uncertainty_count": result["uncertainty_count"]
                        })
                    except Exception as e:
                        logger.error(f"域分析失败: {str(e)}")

            # 按优先级分组
            grouped = self._group_by_priority(all_uncertainties)

            # 保存完整结果到文件
            full_result = {
                "status": "success",
                "connection_name": connection_name,
                "analyzed_at": datetime.now().isoformat(),
                "total_domains": len(domains),
                "domain_results": domain_results,
                "total_uncertainties": len(all_uncertainties),
                "uncertainties_by_priority": grouped,
                "next_step": f"请先回答 {len(grouped['high'])} 个高优先级问题。"
            }

            save_result = self._save_uncertainties(connection_name, full_result)

            # Return lightweight summary (save tokens)
            summary = {
                "status": "success",
                "message": "Uncertainty analysis completed",
                "file_path": save_result.get("file_path"),
                "statistics": {
                    "total_domains": len(domains),
                    "total_uncertainties": len(all_uncertainties),
                    "high_priority": len(grouped['high']),
                    "medium_priority": len(grouped['medium']),
                    "low_priority": len(grouped['low'])
                },
                "next_step": f"请先回答 {len(grouped['high'])} 个高优先级问题。"
            }

            return json.dumps(summary, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    def _analyze_domain(
        self,
        domain_name: str,
        domain_schema: Dict[str, Any],
        model
    ) -> List[Dict[str, Any]]:
        """分析单个域的不确定性"""
        from langchain_core.messages import HumanMessage

        schema_text = self._prepare_domain_schema_text(domain_schema)
# 2. 缺失约束 (missing_constraint) - 缺少外键/唯一/非空约束
# 5. 数据质量担忧 (data_quality_concern) - 数据一致性问题
        prompt = f"""你是数据架构师，分析以下业务域的 schema，识别不确定性。

# 业务域: {domain_name}

{schema_text}

# 任务
识别以下类型的不确定性：
1. Schema 模糊性 (schema_ambiguity) - 表/字段含义不清晰
2. 命名混淆 (naming_confusion) - 命名不一致或缩写不明
3. 业务逻辑不清晰 (business_logic_unclear) - 业务流程无法推断


# 输出格式
只返回 JSON 数组：
```json
[
  {{
    "type": "schema_ambiguity",
    "category": "业务逻辑",
    "priority": "high",
    "entity": "table_name",
    "question": "具体疑问",
    "context": "上下文信息",
    "impact": "影响范围",
    "suggestions": ["建议1", "建议2"]
  }}
]
```

priority: high/medium/low
只识别真正影响分析的不确定性。
"""

        response = model.invoke([HumanMessage(content=prompt)])
        uncertainties = self._extract_json_from_text(response.content)

        if not uncertainties or not isinstance(uncertainties, list):
            logger.warning(f"域 {domain_name} 未返回有效结果")
            return []

        for u in uncertainties:
            u["domain"] = domain_name

        return uncertainties

    def _prepare_domain_schema_text(self, domain_schema: Dict[str, Any]) -> str:
        """准备域 schema 文本（紧凑格式）"""
        lines = []
        lines.append(f"## 域信息")
        lines.append(f"域名: {domain_schema.get('domain_name')}")
        lines.append(f"描述: {domain_schema.get('description')}")
        lines.append(f"表数量: {domain_schema.get('table_count')}\n")

        tables = domain_schema.get("tables", {})
        for table_name, table_data in sorted(tables.items()):
            lines.append(f"### 表: {table_name}")
            if table_data.get("comment"):
                lines.append(f"  注释: {table_data['comment']}")

            # 主键
            if "primary_key" in table_data:
                pk_cols = ", ".join(table_data["primary_key"].get("columns", []))
                lines.append(f"  主键: {pk_cols}")

            # 列（只显示关键信息）
            lines.append("  列:")
            for col in table_data.get("columns", [])[:15]:  # 限制列数
                col_info = f"    - {col['name']} ({col['type']})"
                if col.get("comment"):
                    col_info += f" -- {col['comment']}"
                if not col.get("nullable", True):
                    col_info += " [NOT NULL]"
                lines.append(col_info)

            # 外键
            if table_data.get("foreign_keys"):
                lines.append("  外键:")
                for fk in table_data["foreign_keys"]:
                    fk_info = f"    - {', '.join(fk['columns'])} → {fk['referred_table']}.{', '.join(fk['referred_columns'])}"
                    lines.append(fk_info)

            lines.append("")

        return "\n".join(lines)

    def _extract_json_from_text(self, text: str) -> Optional[Any]:
        """从 AI 输出中提取 JSON"""
        # 策略1：直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略2：查找数组边界 [ ]
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                potential_json = text[start_idx:end_idx+1]
                return json.loads(potential_json)
            except json.JSONDecodeError:
                pass

        # 策略3：markdown 代码块
        if "```" in text:
            try:
                code_start = text.find("```")
                if code_start != -1:
                    json_start = text.find("\n", code_start) + 1
                    code_end = text.find("```", json_start)
                    if code_end != -1:
                        json_text = text[json_start:code_end].strip()
                        return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        logger.warning(f"无法提取 JSON，文本长度: {len(text)}, 前200字符: {text[:200]}")
        return None

    def _group_by_priority(
        self,
        uncertainties: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按优先级分组"""
        grouped = {
            "high": [],
            "medium": [],
            "low": []
        }

        for idx, u in enumerate(uncertainties):
            priority = u.get("priority", "medium").lower()

            # 为每个不确定性生成唯一 ID
            if "id" not in u:
                u["id"] = f"{u.get('domain', 'unknown')}_{u.get('entity', 'unknown')}_{idx}"

            if priority in grouped:
                grouped[priority].append(u)
            else:
                grouped["medium"].append(u)  # 默认归类到 medium

        return grouped

    def _save_uncertainties(
        self,
        connection_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """保存 uncertainties 到文件"""
        try:
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")
            base_dir = Path(schema_path) / connection_name
            base_dir.mkdir(parents=True, exist_ok=True)

            uncertainty_file = base_dir / "uncertainties.json"

            with open(uncertainty_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved uncertainties to {uncertainty_file}")

            return {
                "saved": True,
                "file_path": str(uncertainty_file)
            }

        except Exception as e:
            logger.error(f"Failed to save uncertainties: {str(e)}")
            return {
                "saved": False,
                "error": str(e)
            }
