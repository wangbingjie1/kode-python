"""
AI Uncertainty Analyzer Service

自动分析不确定性问题，通过查询数据库数据来验证和解决问题。
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from kode.core.model_manager import ModelManager
from kode.services.database_manager import db_manager
from kode.utils.config import ConfigManager
from kode.utils.context import get_current_user_id
from kode.utils.logger import setup_logger
from kode.utils.path_utils import get_safe_connection_path
from sqlalchemy import text

logger = setup_logger(__name__)


class UncertaintyAnalyzer:
    """
    AI 不确定性分析器

    逐个分析不确定性问题，通过查询数据库数据生成答案。
    """

    # 可通过数据分析的问题类型
    ANALYZABLE_TYPES = {
        "schema_ambiguity",      # 数据库结构不明确
        "field_ambiguity",       # 字段业务含义不明
        "definition_conflict",   # 业务与数据库定义冲突
        "missing_context",       # 数据库有但业务未说明
        "naming_confusion",      # 命名混淆（可通过数据推断）
        "business_logic_unclear", # 业务逻辑不清
    }

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self.query_timeout = 30  # 单个查询超时秒数
        self.max_rows = 100      # 最大返回行数

    def is_analyzable(self, uncertainty: Dict) -> bool:
        """判断问题是否可通过数据分析"""
        return uncertainty.get("type") in self.ANALYZABLE_TYPES

    async def analyze_uncertainties_stream(
        self,
        connection_name: str,
        uncertainties: List[Dict],
        schema_context: Dict,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        流式分析不确定性问题

        Args:
            connection_name: 数据库连接名
            uncertainties: 待分析的问题列表
            schema_context: schema 上下文信息
            cancel_event: 取消事件

        Yields:
            SSE 事件字典
        """
        # 筛选可分析的问题
        analyzable = []
        skipped = []
        for u in uncertainties:
            if u.get("status") in ["resolved", "skipped"]:
                continue
            if self.is_analyzable(u):
                analyzable.append(u)
            else:
                skipped.append(u)

        total = len(analyzable)
        skipped_types = list(set(u.get("type", "unknown") for u in skipped))

        # 发送开始事件
        yield {
            "type": "start",
            "content": f"开始 AI 分析，共 {total} 个可分析问题",
            "metadata": {
                "total_questions": len(uncertainties),
                "analyzable_count": total,
                "skipped_count": len(skipped),
                "skipped_types": skipped_types,
            }
        }

        if total == 0:
            yield {
                "type": "complete",
                "content": "没有可分析的问题",
                "metadata": {
                    "total_analyzed": 0,
                    "resolved_count": 0,
                    "partial_count": 0,
                    "failed_count": 0,
                }
            }
            return

        resolved_count = 0
        partial_count = 0
        failed_count = 0
        results = []

        for i, uncertainty in enumerate(analyzable):
            # 检查取消
            if cancel_event and cancel_event.is_set():
                yield {
                    "type": "cancelled",
                    "content": "分析已取消",
                    "metadata": {
                        "analyzed_count": i,
                        "total": total,
                    }
                }
                return

            question_id = uncertainty.get("id", f"unknown_{i}")
            question_text = uncertainty.get("question", "")[:80]

            # 发送进度事件
            yield {
                "type": "progress",
                "content": f"正在分析问题 {i + 1}/{total}",
                "metadata": {
                    "current": i + 1,
                    "total": total,
                    "question_id": question_id,
                    "question": question_text,
                    "phase": "analyzing",
                }
            }

            try:
                # 分析单个问题
                result = await self.analyze_single_question(
                    connection_name=connection_name,
                    uncertainty=uncertainty,
                    schema_context=schema_context,
                )

                # 统计
                if result["status"] == "resolved":
                    resolved_count += 1
                elif result["status"] == "partial":
                    partial_count += 1
                else:
                    failed_count += 1

                results.append(result)

                # 发送问题结果事件
                yield {
                    "type": "question_result",
                    "content": result.get("answer", ""),
                    "metadata": result,
                }

            except Exception as e:
                logger.error(f"分析问题 {question_id} 失败: {e}", exc_info=True)
                failed_count += 1
                yield {
                    "type": "question_result",
                    "content": f"分析失败: {str(e)}",
                    "metadata": {
                        "question_id": question_id,
                        "question": uncertainty.get("question", ""),
                        "status": "failed",
                        "error": str(e),
                    }
                }

        # 发送完成事件
        yield {
            "type": "complete",
            "content": f"分析完成，已解决 {resolved_count} 个问题",
            "metadata": {
                "total_analyzed": total,
                "resolved_count": resolved_count,
                "partial_count": partial_count,
                "failed_count": failed_count,
                "results": results,
            }
        }

    async def analyze_single_question(
        self,
        connection_name: str,
        uncertainty: Dict,
        schema_context: Dict,
    ) -> Dict:
        """
        分析单个不确定性问题

        Args:
            connection_name: 数据库连接名
            uncertainty: 不确定性问题
            schema_context: schema 上下文

        Returns:
            分析结果字典
        """
        question_id = uncertainty.get("id", "unknown")
        question = uncertainty.get("question", "")
        entity = uncertainty.get("entity", "")
        context = uncertainty.get("context", "")
        q_type = uncertainty.get("type", "")

        logger.info(f"[AI分析] 开始分析问题: {question_id}")

        # 1. 提取表名和字段名
        tables, fields = self._extract_entities(entity)
        logger.info(f"[AI分析] 提取实体: tables={tables}, fields={fields}")

        if not tables:
            return {
                "question_id": question_id,
                "question": question,
                "status": "failed",
                "error": "无法从问题中提取表名",
                "answer": None,
                "confidence": None,
            }

        # 2. 验证表是否存在
        valid_tables = []
        for table in tables:
            if self._table_exists(connection_name, table):
                valid_tables.append(table)
            else:
                logger.warning(f"[AI分析] 表不存在: {table}")

        if not valid_tables:
            return {
                "question_id": question_id,
                "question": question,
                "status": "failed",
                "error": f"涉及的表都不存在: {tables}",
                "answer": None,
                "confidence": None,
            }

        # 3. 生成 SQL 查询
        sql_queries = await self._generate_sql_queries(
            uncertainty=uncertainty,
            tables=valid_tables,
            fields=fields,
            schema_context=schema_context,
        )

        if not sql_queries:
            return {
                "question_id": question_id,
                "question": question,
                "status": "failed",
                "error": "无法生成有效的 SQL 查询",
                "answer": None,
                "confidence": None,
            }

        # 4. 执行 SQL 查询
        query_results = []
        executed_sqls = []

        for sql_info in sql_queries:
            sql = sql_info.get("sql", "")
            purpose = sql_info.get("purpose", "")

            try:
                result = await self._execute_query_with_timeout(
                    connection_name=connection_name,
                    sql=sql,
                    timeout=self.query_timeout,
                )
                query_results.append({
                    "sql": sql,
                    "purpose": purpose,
                    "status": "success",
                    "data": result,
                })
                executed_sqls.append(sql)
            except asyncio.TimeoutError:
                query_results.append({
                    "sql": sql,
                    "purpose": purpose,
                    "status": "timeout",
                    "error": "查询超时",
                })
            except Exception as e:
                query_results.append({
                    "sql": sql,
                    "purpose": purpose,
                    "status": "error",
                    "error": str(e),
                })

        # 检查是否有成功的查询
        successful_queries = [q for q in query_results if q["status"] == "success"]
        if not successful_queries:
            return {
                "question_id": question_id,
                "question": question,
                "status": "failed",
                "error": "所有 SQL 查询都失败了",
                "sql_executed": executed_sqls,
                "query_results": query_results,
                "answer": None,
                "confidence": None,
            }

        # 5. 分析结果生成答案
        analysis_result = await self._analyze_results_and_generate_answer(
            uncertainty=uncertainty,
            query_results=successful_queries,
        )

        return {
            "question_id": question_id,
            "question": question,
            "status": analysis_result.get("status", "partial"),
            "answer": analysis_result.get("answer"),
            "confidence": analysis_result.get("confidence", "medium"),
            "reasoning": analysis_result.get("reasoning"),
            "sql_executed": executed_sqls,
            "data_summary": analysis_result.get("data_summary"),
        }

    def _extract_entities(self, entity: str) -> Tuple[List[str], List[str]]:
        """
        从 entity 字段提取表名和字段名

        支持格式:
        - "table_name"
        - "table1, table2"
        - "table.field"
        - "table.(field1, field2)"
        - "table1 ↔ table2"

        Returns:
            (tables, fields) 元组
        """
        if not entity:
            return [], []

        tables = []
        fields = []

        # 替换特殊符号
        entity = entity.replace("↔", ",").replace("→", ",")

        # 检查是否有 table.(field1, field2) 格式
        match = re.match(r"(\w+)\.\(([^)]+)\)", entity)
        if match:
            tables.append(match.group(1))
            fields.extend([f.strip() for f in match.group(2).split(",")])
            return tables, fields

        # 检查是否有 table.field 格式
        if "." in entity and "(" not in entity:
            parts = entity.split(".")
            if len(parts) == 2:
                tables.append(parts[0].strip())
                fields.append(parts[1].strip())
                return tables, fields

        # 逗号分隔的表名
        for part in entity.split(","):
            part = part.strip()
            if part:
                # 去掉可能的字段部分
                if "." in part:
                    table_part = part.split(".")[0].strip()
                    tables.append(table_part)
                else:
                    tables.append(part)

        return tables, fields

    def _table_exists(self, connection_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            inspector = db_manager.get_inspector(connection_name)
            table_names = inspector.get_table_names()
            return table_name in table_names
        except Exception:
            return False

    async def _generate_sql_queries(
        self,
        uncertainty: Dict,
        tables: List[str],
        fields: List[str],
        schema_context: Dict,
    ) -> List[Dict]:
        """
        使用 LLM 生成分析 SQL

        Returns:
            [{"sql": "...", "purpose": "..."}]
        """
        question = uncertainty.get("question", "")
        context = uncertainty.get("context", "")
        q_type = uncertainty.get("type", "")
        entity = uncertainty.get("entity", "")

        # 获取相关表的 schema 信息
        table_schemas = []
        for table in tables:
            if table in schema_context.get("tables", {}):
                table_info = schema_context["tables"][table]
                columns = table_info.get("columns", [])
                col_str = ", ".join([f"{c['name']} ({c['type']})" for c in columns[:20]])
                table_schemas.append(f"表 {table}: {col_str}")

        schema_str = "\n".join(table_schemas) if table_schemas else "无可用 schema 信息"

        prompt = f"""根据以下不确定性问题，生成用于分析的 SQL 查询。

问题类型: {q_type}
问题: {question}
上下文: {context}
涉及实体: {entity}
涉及表: {', '.join(tables)}

表结构信息:
{schema_str}

要求:
1. 生成 1-3 个 SQL 查询来验证/回答这个问题
2. 每个查询必须有明确目的
3. 所有 SELECT 查询必须加 LIMIT 100
4. 返回 JSON 格式，格式如下:

```json
[
  {{"sql": "SELECT ...", "purpose": "说明这个查询的目的"}}
]
```

只返回 JSON，不要其他内容。"""

        try:
            model = self.model_manager.get_model("quick")
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.invoke(prompt).content
            )

            # 解析 JSON
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                queries = json.loads(json_match.group())
                # 验证格式
                valid_queries = []
                for q in queries:
                    if isinstance(q, dict) and "sql" in q:
                        valid_queries.append(q)
                return valid_queries

        except Exception as e:
            logger.error(f"生成 SQL 失败: {e}")

        # 回退：使用预定义的 SQL 模板
        return self._generate_fallback_sql(tables, fields, q_type)

    def _generate_fallback_sql(
        self,
        tables: List[str],
        fields: List[str],
        q_type: str,
    ) -> List[Dict]:
        """生成回退 SQL（当 LLM 失败时）"""
        queries = []

        for table in tables[:2]:  # 最多处理 2 个表
            # 基础：统计表数据量
            queries.append({
                "sql": f"SELECT COUNT(*) as total_count FROM {table}",
                "purpose": f"统计 {table} 表的数据量",
            })

            # 抽样数据
            queries.append({
                "sql": f"SELECT * FROM {table} LIMIT 10",
                "purpose": f"查看 {table} 表的样例数据",
            })

        # 如果有字段，统计字段值分布
        if fields and tables:
            for field in fields[:2]:
                queries.append({
                    "sql": f"SELECT {field}, COUNT(*) as cnt FROM {tables[0]} WHERE {field} IS NOT NULL GROUP BY {field} ORDER BY cnt DESC LIMIT 20",
                    "purpose": f"分析 {field} 字段的值分布",
                })

        # 如果是表关系问题且有多个表
        if len(tables) >= 2 and q_type == "schema_ambiguity":
            t1, t2 = tables[0], tables[1]
            queries.append({
                "sql": f"SELECT '{t1}' as table_name, COUNT(*) as cnt FROM {t1} UNION ALL SELECT '{t2}', COUNT(*) FROM {t2}",
                "purpose": f"对比 {t1} 和 {t2} 的数据量",
            })

        return queries

    async def _execute_query_with_timeout(
        self,
        connection_name: str,
        sql: str,
        timeout: int,
    ) -> Dict:
        """执行 SQL 查询（带超时）"""
        def _execute():
            engine = db_manager.get_engine(connection_name)
            with engine.connect() as conn:
                result = conn.execute(text(sql))

                # SELECT 查询返回数据
                if sql.strip().upper().startswith("SELECT"):
                    rows = result.fetchmany(self.max_rows)
                    columns = list(result.keys()) if result.keys() else []
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            val = row[i]
                            # 处理不可序列化的类型
                            if isinstance(val, (datetime,)):
                                val = val.isoformat()
                            elif isinstance(val, bytes):
                                val = val.hex()[:50] + "..."
                            row_dict[col] = val
                        data.append(row_dict)
                    return {
                        "columns": columns,
                        "rows": data,
                        "row_count": len(data),
                    }
                else:
                    # INSERT/UPDATE/DELETE
                    return {
                        "affected_rows": result.rowcount,
                    }

        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _execute),
            timeout=timeout,
        )

    async def _analyze_results_and_generate_answer(
        self,
        uncertainty: Dict,
        query_results: List[Dict],
    ) -> Dict:
        """
        分析查询结果，生成答案

        Returns:
            {
                "status": "resolved" | "partial" | "failed",
                "answer": str,
                "confidence": "high" | "medium" | "low",
                "reasoning": str,
                "data_summary": dict,
            }
        """
        question = uncertainty.get("question", "")
        context = uncertainty.get("context", "")
        entity = uncertainty.get("entity", "")

        # 构建数据摘要
        data_summary = []
        for qr in query_results:
            sql = qr.get("sql", "")
            purpose = qr.get("purpose", "")
            data = qr.get("data", {})

            if "rows" in data:
                row_count = data.get("row_count", 0)
                rows_preview = data.get("rows", [])[:5]  # 只取前 5 行
                data_summary.append({
                    "sql": sql,
                    "purpose": purpose,
                    "row_count": row_count,
                    "sample_data": rows_preview,
                })
            elif "affected_rows" in data:
                data_summary.append({
                    "sql": sql,
                    "purpose": purpose,
                    "affected_rows": data.get("affected_rows"),
                })

        # 使用 LLM 分析结果
        prompt = f"""根据以下数据库查询结果，回答不确定性问题。

问题: {question}
上下文: {context}
涉及实体: {entity}

查询结果:
{json.dumps(data_summary, indent=2, ensure_ascii=False, default=str)}

要求:
1. 基于数据给出明确、具体的答案
2. 说明推理过程
3. 评估答案的置信度 (high/medium/low)
4. 如果数据不足以完全回答问题，说明原因

返回 JSON 格式:
```json
{{
  "status": "resolved 或 partial 或 failed",
  "answer": "基于数据分析的答案",
  "confidence": "high 或 medium 或 low",
  "reasoning": "推理过程说明"
}}
```

只返回 JSON，不要其他内容。"""

        try:
            model = self.model_manager.get_model("quick")
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.invoke(prompt).content
            )

            # 解析 JSON
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                result = json.loads(json_match.group())
                result["data_summary"] = data_summary
                return result

        except Exception as e:
            logger.error(f"分析结果失败: {e}")

        # 回退：返回简单结果
        return {
            "status": "partial",
            "answer": f"已查询到相关数据，但无法自动生成结论。请根据数据手动分析。",
            "confidence": "low",
            "reasoning": "LLM 分析失败，返回原始数据",
            "data_summary": data_summary,
        }


def get_schema_context(connection_name: str, user_id: str = None) -> Dict:
    """
    获取数据库 schema 上下文

    Args:
        connection_name: 数据库连接名
        user_id: 用户 ID

    Returns:
        schema 上下文字典
    """
    config = ConfigManager()
    schema_path = config.get("storage.schema_path", "./schema_store")

    if user_id is None:
        user_id = get_current_user_id()

    safe_conn_name = get_safe_connection_path(connection_name)
    schema_dir = Path(schema_path) / user_id / safe_conn_name

    # 尝试加载 schema 文件
    schema_file = schema_dir / "schema_latest.json"
    if not schema_file.exists():
        # 尝试其他可能的文件名
        for f in schema_dir.glob("schema_*.json"):
            schema_file = f
            break

    if schema_file.exists():
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 schema 文件失败: {e}")

    return {"tables": {}}
