"""Ontology building and storage tools for database schema understanding."""

import json
from datetime import datetime
from logging import log
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from kode.tools.base import KodeTool
from kode.core.model_manager import ModelManager
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)

# ==================== Tool Input Schemas ====================


class OntologyBuilderInput(BaseModel):
    """Input schema for OntologyBuilderTool."""

    connection_name: str = Field(
        description="Database connection name. The tool will load schema from schema_store/{connection_name}/schema_latest.json"
    )
    use_llm_enrichment: bool = Field(
        default=False, description="Use LLM to enrich ontology with business semantics"
    )
    add_business_terms: bool = Field(
        default=True, description="Convert technical names to business terms"
    )
    infer_relationships: bool = Field(
        default=True, description="Infer implicit relationships beyond FK constraints"
    )
    extract_hierarchies: bool = Field(
        default=True, description="Extract hierarchical relationships"
    )
    auto_save: bool = Field(default=True, description="Automatically save ontology to file")
    version: str = Field(default="auto", description="Version identifier (auto = timestamp)")


class OntologySearchInput(BaseModel):
    """Input schema for OntologySearchTool."""

    ontology_path: str = Field(description="Path to ontology storage")
    query: str = Field(description="Search query (natural language)")
    search_type: str = Field(
        default="semantic", description="Search type: semantic, exact, fuzzy"
    )
    top_k: int = Field(default=5, description="Number of results to return")


# ==================== Ontology Tools ====================


class OntologyBuilderTool(KodeTool):
    """
    Build business ontology from database schema.

    Converts technical database schema to semantic business ontology,
    enriching with business terms and relationships.

    IMPORTANT: This tool loads schema from schema_store/{connection_name}/schema_latest.json.
    You must run DatabaseSchemaExtractor first to extract and save the schema.
    """

    name: str = "OntologyBuilder"
    description: str = """Build business ontology from database schema.

    Prerequisites: Must run DatabaseSchemaExtractor first to save schema to file.

    This tool:
    1. Loads schema from schema_store/{connection_name}/schema_latest.json
    2. Converts tables to business concepts/entities
    3. Converts columns to properties/attributes
    4. Extracts relationships (FK constraints + inferred)
    5. Identifies hierarchical structures
    6. Optionally enriches with LLM-generated business semantics
    7. Saves ontology to ontology_store/{connection_name}/

    Input: connection_name (string), NOT the full schema JSON."""

    args_schema: Type[BaseModel] = OntologyBuilderInput
    requires_permission: bool = False

    def _run(
        self,
        connection_name: str,
        use_llm_enrichment: bool = False,
        add_business_terms: bool = True,
        infer_relationships: bool = True,
        extract_hierarchies: bool = True,
        auto_save: bool = True,
        version: str = "auto",
    ) -> str:
        """
        Build ontology from database schema using AI.

        Args:
            connection_name: Database connection name (loads schema from schema_store)
            use_llm_enrichment: Use LLM for enrichment (DEPRECATED - always uses LLM now)
            add_business_terms: Convert to business terms (DEPRECATED - LLM handles this)
            infer_relationships: Infer implicit relationships (DEPRECATED - LLM handles this)
            extract_hierarchies: Extract hierarchies (DEPRECATED - LLM handles this)
            auto_save: Automatically save ontology to file
            version: Version identifier

        Returns:
            Ontology as JSON
        """
        try:
            # Load schema from saved file
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")
            schema_file = Path(schema_path) / connection_name / "schema_latest.json"

            if not schema_file.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Schema file not found for connection '{connection_name}'",
                        "expected_path": str(schema_file),
                        "suggestion": "Run DatabaseSchemaExtractor first to extract schema",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # 【智能门禁检查】检查不确定性分析状态（从各领域文件中读取）
            # ✨ 新架构：不确定性数据已分散存储在各 domain JSON 文件中
            domains_dir = Path(schema_path) / connection_name / "domains"

            if not domains_dir.exists() or not list(domains_dir.glob("*.json")):
                # 🔍 情况1: 没有领域文件 → Schema 未提取
                logger.warning(f"⚠️ 未找到 domains 目录或领域文件")
                return json.dumps(
                    {
                        "status": "error",
                        "gate_check_failed": True,
                        "reason": "missing_schema_extraction",
                        "message": "未找到领域schema文件。",
                        "suggestion": "请先运行 DatabaseSchemaExtractor 提取数据库schema。",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # 🔍 情况2: 读取所有领域文件，检查 high 优先级不确定性
            high_uncertainties = []
            for domain_file in domains_dir.glob("*.json"):
                try:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        domain_data = json.load(f)

                    # 从领域文件中读取 uncertainties
                    uncertainties = domain_data.get("uncertainties", [])
                    high_uncertainties.extend([
                        u for u in uncertainties
                        if u.get("priority") == "high"
                    ])
                except Exception as e:
                    logger.warning(f"读取领域文件 {domain_file.name} 失败: {e}")
            unresolved_high = [
                u for u in high_uncertainties
                if u.get("status") not in ["resolved", "skipped"]
            ]

            if unresolved_high:
                # 生成问题列表（前5个）
                question_list = "\n".join([
                    f"  {i+1}. [{u.get('domain')}] {u.get('question')}"
                    for i, u in enumerate(unresolved_high[:5])
                ])

                return json.dumps(
                    {
                        "status": "error",
                        "gate_check_failed": True,
                        "reason": "unresolved_high_priority_uncertainties",
                        "message": f"❌ 不能构建本体！发现 {len(unresolved_high)} 个未解决的高优先级问题。",
                        "unresolved_count": len(unresolved_high),
                        "total_high_count": len(high_uncertainties),
                        "sample_questions": question_list,
                        "suggestion": "必须先回答所有 high 优先级问题（这些问题严重影响本体质量）。",
                        "action_required": f"运行 UncertaintyQAManager(connection_name='{connection_name}', action='batch_load') 查看所有问题",
                        "note": "不要重复运行 DomainUncertaintyAnalyzer，uncertainties.json 已存在。"
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # ✅ 情况3: 所有 high 问题已解决
            resolved_count = len([u for u in high_uncertainties if u.get("status") in ["resolved", "skipped"]])
            logger.info(f"✅ 门禁检查通过：所有 {len(high_uncertainties)} 个高优先级问题已解决（resolved: {resolved_count}）")

            # Load schema data
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            # Unwrap schema if it has version wrapper
            if "schema" in schema_data and isinstance(schema_data["schema"], dict):
                schema_metadata = schema_data["schema"]
            else:
                schema_metadata = schema_data

            # 🚀 新的简化流程：优先使用 domain_index.json（如果存在）
            domain_index_file = Path(schema_path) / connection_name / "domain_index.json"
            database = schema_metadata.get("database", "未知")
            db_schema = schema_metadata.get("schema")

            import asyncio

            # 策略选择：如果有 domain_index.json，使用简化并行流程
            if domain_index_file.exists():
                logger.info(f"✅ 检测到 domain_index.json，使用简化并行构建流程")

                # 🔥 关键：在已运行的事件循环中，需要在新线程中运行 asyncio.run
                def run_async_in_thread():
                    """在新线程中运行异步任务（避免嵌套事件循环冲突）"""
                    return asyncio.run(
                        self._build_ontology_from_domains_async(
                            connection_name, database, db_schema, schema_path
                        )
                    )

                try:
                    loop = asyncio.get_running_loop()
                    # 在事件循环中，使用线程池运行
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_async_in_thread)
                        ontology = future.result()
                except RuntimeError:
                    # 不在事件循环中，直接运行
                    ontology = run_async_in_thread()
            else:
                # domain_index.json 不存在，报错
                return json.dumps({
                    "status": "error",
                    "message": "domain_index.json not found. Please run DomainClusteringTool first to cluster the schema into domains."
                }, indent=2, ensure_ascii=False)

            # Auto-save ontology to file
            if auto_save:
                save_result = self._save_ontology(ontology, connection_name, version)
                ontology["storage"] = save_result

            # Return lightweight summary instead of full ontology (save tokens)
            summary = {
                "status": "success",
                "message": "Ontology built successfully",
                "file_path": ontology.get("storage", {}).get("latest_path", ""),
                "statistics": {
                    "concept_count": len(ontology.get("concepts", {})),
                    "relationship_count": len(ontology.get("relationships", [])),
                    "uncertainty_count": len(ontology.get("uncertainties", []))
                },
                "metadata": ontology.get("metadata", {})
            }

            return json.dumps(summary, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to build ontology: {str(e)}",
                },
                indent=2,
            )

    def _prepare_schema_for_ai(self, schema_metadata: Dict[str, Any]) -> str:
        """
        将数据库 schema 转换为紧凑的、AI 友好的格式。

        包含：表名、列信息（名称、类型、注释、默认值）、主键、唯一约束、外键关系。

        增强版本：补充了默认值和唯一约束，以完整保留业务规则信息。
        """
        tables = schema_metadata.get("tables", {})
        relationships = schema_metadata.get("relationships", [])

        lines = []
        lines.append(f"数据库: {schema_metadata.get('database', '未知')}")
        lines.append(f"表数量: {len(tables)}")
        lines.append("")

        # 表和列信息
        for table_name, table_data in tables.items():
            lines.append(f"## {table_name} -- {table_data.get('comment', '')}")

            # 主键
            if "primary_key" in table_data:
                pk_cols = ", ".join(table_data["primary_key"].get("columns", []))
                lines.append(f"  主键: {pk_cols}")

            # 列
            lines.append("  列:")
            for col in table_data.get("columns", []):
                col_info = f"    - {col['name']} ({col['type']})"
                if col.get("comment"):
                    col_info += f" -- {col['comment']}"
                if not col.get("nullable", True):
                    col_info += " [NOT NULL]"
                if col.get("autoincrement"):
                    col_info += " [AUTO_INCREMENT]"
                # ✨ 新增：默认值（重要的业务初始状态）
                if col.get("default") and str(col["default"]).lower() != "null":
                    col_info += f" [DEFAULT: {col['default']}]"
                lines.append(col_info)

            # ✨ 新增：唯一约束（重要的业务规则）
            if table_data.get("indexes"):
                unique_indexes = [idx for idx in table_data["indexes"] if idx.get("unique")]
                if unique_indexes:
                    lines.append("  唯一约束:")
                    for idx in unique_indexes:
                        idx_cols = ", ".join(idx.get("columns", []))
                        idx_name = idx.get("name", "unnamed")
                        lines.append(f"    - {idx_cols} ({idx_name})")

            lines.append("")

        # 外键关系
        if relationships:
            lines.append("## 外键关系")
            for rel in relationships:
                lines.append(
                    f"  {rel['from_table']}.{','.join(rel['from_columns'])} → "
                    f"{rel['to_table']}.{','.join(rel['to_columns'])}"
                )

        return "\n".join(lines)

    def _create_ontology_generation_prompt(self, schema_summary: str, connection_name: str, database: str, db_schema: Optional[str]) -> str:
        """创建用于本体生成的 AI prompt。"""
        return f"""你是一位资深的 ERP 系统架构师和业务分析专家。请分析以下数据库 schema，构建一个完整的业务本体（Ontology）。

# 数据库 Schema

连接名称: {connection_name}
数据库: {database}
Schema: {db_schema or "默认"}

{schema_summary}

# 任务要求

请深入理解这个数据库的业务语义，生成一个完整的业务本体，包括：

1. **Concepts（概念/实体）**: 每个表代表的业务概念
   - technical_name: 技术名称（表名）
   - business_name_cn: 中文业务名称
   - business_name_en: 英文业务名称
   - description: 业务描述（100字以内，说清楚这个概念的业务含义）
   - domain: 所属业务领域（如：用户管理、订单管理、财务管理等）
   - importance: 重要性 (critical/high/medium/low)
   - primary_key: 主键字段列表
   - data_source: 数据来源信息
     - connection_name: 数据库连接名称
     - database: 数据库名称
     - schema: Schema名称（可选）
     - table_name: 表名

2. **Properties（属性）**: 每个字段的业务含义
   - technical_name: 技术名称（表名.字段名）
   - business_name_cn: 中文业务名称
   - business_name_en: 英文业务名称
   - description: 业务含义描述
   - data_type: 数据类型
   - nullable: 是否可空
   - concept: 所属概念（表名）
   - data_source: 数据来源信息
     - connection_name: 数据库连接名称
     - database: 数据库名称
     - schema: Schema名称（可选）
     - table_name: 表名
     - column_name: 字段名

3. **Relationships（关系）**: 表之间的业务关系
   - from_concept: 源概念
   - to_concept: 目标概念
   - relationship_type: 关系类型（foreign_key/one_to_many/many_to_many/composition/aggregation）
   - cardinality: 基数（1:1, 1:N, N:M）
   - business_meaning: 业务含义（如："订单属于用户"、"商品属于分类"）
   - from_properties: 源字段
   - to_properties: 目标字段

4. **Hierarchies（层次结构）**: 识别树形/层级结构
   - concept: 概念名称
   - type: 类型（self_referencing/category_tree/organizational_tree等）
   - parent_property: 父节点字段
   - description: 业务描述

5. **Domain Insights（领域洞察）**:
   - primary_domain: 主要业务领域
   - sub_domains: 子领域列表
   - business_scenario: 业务场景描述
   - architecture_pattern: 架构模式（单体/微服务/领域驱动）

6. **Business Rules（业务规则）**: 从 schema 推断的业务规则
   - 唯一性约束
   - 必填字段的业务含义
   - 数据完整性规则

7. **Uncertainties（不确定性列表）**: 基于 schema 分析得出的困扰点和不利于分析的因素
   - type: 不确定性类型（schema_ambiguity/missing_constraint/naming_confusion/business_logic_unclear/data_quality_concern）
   - category: 分类（数据模型/业务逻辑/命名规范/数据质量/关系推断）
   - priority: 优先级（high/medium/low）
   - entity: 相关实体（表名或 "整体"）
   - question: 具体的疑问或困扰描述
   - context: 产生困扰的上下文信息
   - impact: 影响范围描述

# 输出格式

请严格按照以下 JSON 格式输出，不要有任何多余的文字解释，直接输出 JSON 字符串：

```json
{{
  "concepts": {{
    "table_name": {{
      "technical_name": "table_name",
      "business_name_cn": "中文名",
      "business_name_en": "English Name",
      "description": "详细的业务描述",
      "domain": "业务领域",
      "importance": "high",
      "primary_key": ["id"],
      "data_source": {{
        "connection_name": "{connection_name}",
        "database": "{database}",
        "schema": "{db_schema or ""}",
        "table_name": "table_name"
      }}
    }}
  }},
  "properties": {{
    "table_name.column_name": {{
      "technical_name": "table_name.column_name",
      "business_name_cn": "中文属性名",
      "business_name_en": "English Property Name",
      "description": "属性的业务含义",
      "data_type": "VARCHAR",
      "nullable": false,
      "concept": "table_name",
      "data_source": {{
        "connection_name": "{connection_name}",
        "database": "{database}",
        "schema": "{db_schema or ""}",
        "table_name": "table_name",
        "column_name": "column_name"
      }}
    }}
  }},
  "relationships": [
    {{
      "from_concept": "orders",
      "to_concept": "users",
      "relationship_type": "foreign_key",
      "cardinality": "N:1",
      "business_meaning": "订单属于用户",
      "from_properties": ["user_id"],
      "to_properties": ["id"]
    }}
  ],
  "hierarchies": [
    {{
      "concept": "categories",
      "type": "category_tree",
      "parent_property": "parent_id",
      "description": "商品分类形成树形结构"
    }}
  ],
  "domain_insights": {{
    "primary_domain": "电商平台",
    "sub_domains": ["用户管理", "订单管理", "商品管理"],
    "business_scenario": "B2C电商平台，支持用户注册、商品浏览、下单购买",
    "architecture_pattern": "单体应用"
  }},
  "uncertainties": [
    {{
      "type": "missing_constraint",
      "category": "数据模型",
      "priority": "high",
      "entity": "orders",
      "question": "订单表有多个，无法区分",
      "context": "订单表order，platform_trade_order",
      "impact": "影响订单状态管理、订单查询、业务分析等核心功能"
    }},
    {{
      "type": "schema_ambiguity",
      "category": "业务逻辑",
      "priority": "medium",
      "entity": "整体",
      "question": "缺少用户行为日志表，无法进行用户行为分析",
      "context": "当前 schema 仅有业务实体表（用户、订单、商品），缺少日志/事件表",
      "impact": "限制了用户行为分析、推荐系统、安全审计等高级功能"
    }}
  ]
}}
```

注意：
- 必须为每个表生成 concept
- 必须为每个字段生成 property
- 充分利用字段注释（comment）来理解业务含义
- 推断隐式关系（如字段名包含 _id 后缀）
- 识别常见的业务模式（用户-订单、分类-商品等）
- 描述要准确、专业，体现对业务的深入理解
- **重点关注不确定性（uncertainties）**：
  * 仔细分析 schema 中的模糊点、缺失约束、命名不清晰等问题
  * 从数据分析师/架构师的角度思考：哪些地方会让你困惑？哪些信息缺失会阻碍业务分析？
  * 每个不确定性必须包含具体的 question（疑问）、context（上下文）、suggestions（解决建议）
  * 优先级判断：high（严重影响数据分析和业务理解）、medium（有一定影响）、low（轻微影响）
"""

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从 AI 输出中提取 JSON（优化版本，快速失败）。"""
        # 策略1：直接解析（最快）
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略2：查找 { } 边界（常见情况）
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                potential_json = text[start_idx:end_idx+1]
                parsed = json.loads(potential_json)
                # 验证是本体JSON
                if "concepts" in parsed or "properties" in parsed or "business_domains" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # 策略3：markdown 代码块（最后尝试，只匹配第一个）
        if "```" in text:
            # 简单提取，不用正则
            try:
                code_start = text.find("```")
                if code_start != -1:
                    # 跳过语言标识（json）
                    json_start = text.find("\n", code_start) + 1
                    code_end = text.find("```", json_start)
                    if code_end != -1:
                        json_text = text[json_start:code_end].strip()
                        return json.loads(json_text)
            except (json.JSONDecodeError, ValueError):
                pass

        logger.warning(f"无法提取JSON，文本长度: {len(text)}, 前200字符: {text[:200]}")
        return None

    def _save_ontology(
        self, ontology: Dict[str, Any], connection_name: str, version: str
    ) -> Dict[str, Any]:
        """
        Save ontology to file with version control.

        Args:
            ontology: Ontology data to save
            connection_name: Database connection name
            version: Version identifier

        Returns:
            Storage metadata
        """
        try:
            # Get storage path from config
            config = ConfigManager()
            storage_path = config.get("storage.ontology_path", "./ontology_store")

            # Create storage directory
            base_dir = Path(storage_path)
            conn_dir = base_dir / connection_name
            conn_dir.mkdir(parents=True, exist_ok=True)

            # Generate version
            if version == "auto":
                version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Prepare ontology with metadata
            ontology_with_meta = {
                "version": version,
                "created_at": datetime.now().isoformat(),
                "connection_name": connection_name,
                "ontology": ontology,
            }

            # Save versioned file
            version_file = conn_dir / f"ontology_{version}.json"
            with open(version_file, "w", encoding="utf-8") as f:
                json.dump(ontology_with_meta, f, indent=2, ensure_ascii=False)

            # Update latest pointer (使用 copy 而不是重复写入)
            import shutil
            latest_file = conn_dir / "ontology_latest.json"
            shutil.copy2(version_file, latest_file)

            return {
                "saved": True,
                "version": version,
                "version_file": str(version_file),
                "latest_file": str(latest_file),
            }

        except Exception as e:
            return {
                "saved": False,
                "error": str(e),
            }


    def _prepare_domain_schema(self, domain_schema: Dict[str, Any]) -> str:
        """为域准备详细schema文本（含样例数据智能摘要）。"""
        lines = []
        for table_name, table_data in sorted(domain_schema.items()):
            lines.append(f"## {table_name} -- {table_data.get('comment', '')}")
            if "primary_key" in table_data:
                lines.append(f"  主键: {', '.join(table_data['primary_key'].get('columns', []))}")
            lines.append("  列:")
            for col in table_data.get("columns", []):
                col_info = f"    - {col['name']} ({col['type']})"
                if col.get("comment"):
                    col_info += f" -- {col['comment']}"
                if not col.get("nullable", True):
                    col_info += " [NOT NULL]"
                if col.get("default") and str(col["default"]).lower() != "null":
                    col_info += f" [DEFAULT: {col['default']}]"
                lines.append(col_info)
            if table_data.get("indexes"):
                unique_indexes = [idx for idx in table_data["indexes"] if idx.get("unique")]
                if unique_indexes:
                    lines.append("  唯一约束:")
                    for idx in unique_indexes:
                        lines.append(f"    - {', '.join(idx.get('columns', []))}")

            # 添加样例数据（直接给AI所有数据）
            sample_data = table_data.get("sample_data", {})
            if sample_data and sample_data.get("rows"):
                rows = sample_data["rows"]
                row_count = sample_data.get("row_count", len(rows))
                lines.append(f"  样例数据({row_count}条):")
                for row in rows:
                    lines.append(f"    {json.dumps(row, ensure_ascii=False)}")

            lines.append("")
        return "\n".join(lines)

    def _merge_ontologies(self, domain_ontologies: Dict[str, Dict[str, Any]], cross_domain_insights: Dict[str, Any],
                         global_context: Dict[str, Any], schema_metadata: Dict[str, Any],
                         connection_name: str, model_manager) -> Dict[str, Any]:
        """合并所有域的本体+跨域洞察。"""
        all_concepts, all_properties, all_relationships, all_hierarchies, all_uncertainties = {}, {}, [], [], []

        for ont in domain_ontologies.values():
            all_concepts.update(ont.get("concepts", {}))
            all_properties.update(ont.get("properties", {}))
            all_relationships.extend(ont.get("relationships", []))
            all_hierarchies.extend(ont.get("hierarchies", []))
            all_uncertainties.extend(ont.get("uncertainties", []))

        all_relationships.extend(cross_domain_insights.get("relationships", []))
        all_hierarchies.extend(cross_domain_insights.get("global_hierarchies", []))

        domain_insights = cross_domain_insights.get("global_insights", {})
        if not domain_insights:
            domain_insights = {
                "primary_domain": global_context.get("architecture_pattern", "未知"),
                "sub_domains": list(domain_ontologies.keys()),
                "business_scenario": global_context.get("insights", ""),
                "architecture_pattern": global_context.get("architecture_pattern", "未知")
            }

        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "created_by": "ai_three_phase",
                "model": model_manager.get_current_model_name(),
                "source_database": schema_metadata.get("database"),
                "source_connection": connection_name,
                "table_count": schema_metadata.get("table_count", 0),
                "build_method": "three_phase_batched",
                "phase1_domains": len(global_context.get("business_domains", {})),
                "phase2_domains": len(domain_ontologies),
                "phase3_cross_relations": len(cross_domain_insights.get("relationships", []))
            },
            "concepts": all_concepts,
            "properties": all_properties,
            "relationships": all_relationships,
            "hierarchies": all_hierarchies,
            "domain_insights": domain_insights,
            "uncertainties": all_uncertainties,
            "recommendations": [],
            "statistics": {
                "concept_count": len(all_concepts),
                "property_count": len(all_properties),
                "relationship_count": len(all_relationships),
                "hierarchy_count": len(all_hierarchies),
                "uncertainty_count": len(all_uncertainties),
            },
        }

    # ==================== 新增：简化并行构建流程（基于 domain_index.json） ====================

    async def _build_ontology_from_domains_async(
        self, connection_name: str, database: str, db_schema: Optional[str], schema_path: str
    ) -> Dict[str, Any]:
        """
        🚀 简化版：直接基于已分域的 schema 文件并行构建本体（异步版本）。

        前提：DomainUncertaintyAnalyzer 已将 schema 分成多个 domain 文件。
        优势：
        - 跳过阶段1（全局架构扫描）→ 节省 ~6秒
        - 跳过阶段3（跨域关系融合）→ 节省 ~5秒
        - 直接并行构建所有域 → 总耗时 ~8秒（原 ~17秒）
        """
        try:
            import time
            from langchain_core.messages import HumanMessage

            # 1. 读取 domain_index.json
            domain_index_file = Path(schema_path) / connection_name / "domain_index.json"
            with open(domain_index_file, "r", encoding="utf-8") as f:
                domain_index = json.load(f)

            domains = domain_index["domains"]
            logger.info(f"📋 加载到 {len(domains)} 个业务域")

            # 2. 初始化模型
            config_manager = ConfigManager()
            config = config_manager.get_all()
            model_manager = ModelManager(config)
            model = model_manager.get_model("main")
            model.temperature = 0.0
            model.max_tokens = 64000

            # 3. 并行构建所有域
            t_start = time.time()
            domain_ontologies = await self._build_all_domains_parallel(
                domains=domains,
                connection_name=connection_name,
                schema_path=schema_path,
                database=database,
                db_schema=db_schema,
                model=model
            )
            t_elapsed = time.time() - t_start
            logger.info(f"✅ 并行构建完成：{len(domain_ontologies)} 个域，耗时 {t_elapsed:.2f}s")

            # 4. 轻量级合并（无需AI）
            final_ontology = self._merge_domain_ontologies_simple(
                domain_ontologies=domain_ontologies,
                connection_name=connection_name,
                database=database,
                model_manager=model_manager
            )

            logger.info(f"🎉 本体构建完成：{final_ontology['statistics']['concept_count']} 个概念")
            return final_ontology

        except Exception as e:
            logger.error(f"简化构建失败: {str(e)}")
            return {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": "error_simplified",
                    "error": str(e),
                },
                "concepts": {},
                "properties": {},
                "relationships": [],
                "hierarchies": [],
            }


    async def _build_all_domains_parallel(
        self,
        domains: List[Dict[str, Any]],
        connection_name: str,
        schema_path: str,
        database: str,
        db_schema: Optional[str],
        model
    ) -> Dict[str, Dict[str, Any]]:
        """
        并行构建所有业务域的本体（核心性能优化）。

        使用 asyncio.gather() + Semaphore(5) 限流，避免 API 限速。
        """
        import asyncio
        import time

        async def build_single_domain(domain_info: Dict[str, Any]) -> tuple:
            """异步构建单个域。"""
            domain_name = domain_info["name"]
            t_start = time.time()
            logger.info(f"🚀 开始构建 {domain_name}（{domain_info['table_count']} 个表）")

            # 读取领域的完整 schema
            domain_file = Path(schema_path) / connection_name / domain_info["file_path"]
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            # 异步调用 AI 构建本体
            t_ai_start = time.time()
            domain_ont = await self._ai_build_domain_ontology(
                domain_name=domain_name,
                domain_schema=domain_data.get("tables", {}),
                connection_name=connection_name,
                database=database,
                db_schema=db_schema,
                model=model
            )
            t_ai_elapsed = time.time() - t_ai_start

            t_elapsed = time.time() - t_start
            logger.info(f"✅ {domain_name} 完成（{domain_info['table_count']} 个表，AI耗时 {t_ai_elapsed:.2f}s，总耗时 {t_elapsed:.2f}s）")
            return domain_name, domain_ont

        # 限流并发（最多5个同时）
        from asyncio import Semaphore
        semaphore = Semaphore(10)

        async def bounded_task(domain_info):
            async with semaphore:
                return await build_single_domain(domain_info)

        # 并行执行
        results = await asyncio.gather(*[bounded_task(d) for d in domains])

        # 转换为字典
        return {domain_name: ontology for domain_name, ontology in results}

    async def _ai_build_domain_ontology(
        self,
        domain_name: str,
        domain_schema: Dict[str, Any],
        connection_name: str,
        database: str,
        db_schema: Optional[str],
        model
    ) -> Dict[str, Any]:
        """
        为单个业务域构建本体（异步并行化版本）。

        关键简化：不再需要全局上下文，直接基于领域 schema 生成。
        """
        from langchain_core.messages import HumanMessage

        # 准备领域 schema 文本
        domain_schema_text = self._prepare_domain_schema(domain_schema)

        # 🔥 新增：加载并注入High优先级不确定性的答案（极致压缩）
        uncertainty_rules = self._load_high_priority_rules(connection_name, domain_name)
        uncertainty_section = ""
        if uncertainty_rules:
            uncertainty_section = "\n\n# 🔒 用户已确认的业务规则（必须遵守）\n\n"
            uncertainty_section += uncertainty_rules
            uncertainty_section += "\n**重要**: 构建本体时必须严格遵循上述规则！\n"

        # 简化版 Prompt（无全局上下文）
        prompt = f"""你是 ERP 架构师。为业务域 "{domain_name}" 构建详细本体。

# 当前域: {domain_name}
数据库: {database}
Schema: {db_schema or "默认"}
{uncertainty_section}
{domain_schema_text}

# 任务
构建本体（JSON格式）：
1. **Concepts**: 每个表转换为业务概念
   - technical_name, business_name_cn, business_name_en
   - description（业务含义）
   - domain（固定为 "{domain_name}"）
   - importance, primary_key, data_source

2. **Properties**: 每个字段转换为业务属性
   - technical_name (table.column), business_name_cn, business_name_en
   - description, data_type, nullable, concept, data_source

3. **Relationships**: 表之间的关系（含外键+推断关系）
   - from_concept, to_concept, relationship_type, cardinality
   - business_meaning, from_properties, to_properties

4. **Hierarchies**: 层次结构（如自引用、分类树）
   - concept, type, parent_property, description

# 输出格式
```json
{{{{
  "concepts": {{}},
  "properties": {{}},
  "relationships": [],
  "hierarchies": [],
  "domain_insights": {{{{
    "primary_domain": "{domain_name}",
    "business_scenario": "..."
  }}}}
}}}}
```

**重要**：
- 必须为该域的每个表生成 concept
- 必须为每个字段生成 property
- 充分利用字段注释理解业务含义
- 只返回 JSON，不要任何解释文字
"""

        # 异步调用 AI
        response = await model.ainvoke([HumanMessage(content=prompt)])
        ontology_data = self._extract_json_from_text(response.content)

        if not ontology_data or "concepts" not in ontology_data:
            logger.error(f"❌ 域 {domain_name} 生成失败，AI输出前500字符: {response.content[:500]}")
            return {
                "concepts": {},
                "properties": {},
                "relationships": [],
                "hierarchies": [],
                "domain_insights": {},
                "uncertainties": []
            }

        # 加载不确定性数据（结构化数据）
        uncertainties = self._load_high_priority_rules_data(connection_name, domain_name)

        return {
            "concepts": ontology_data.get("concepts", {}),
            "properties": ontology_data.get("properties", {}),
            "relationships": ontology_data.get("relationships", []),
            "hierarchies": ontology_data.get("hierarchies", []),
            "domain_insights": ontology_data.get("domain_insights", {}),
            "uncertainties": uncertainties
        }


    def _load_high_priority_rules_data(self, connection_name: str, domain_name: str) -> List[Dict[str, Any]]:
        """
        加载领域的所有不确定性数据（原样返回，用于保存到本体文件）。

        ✨ 新架构：从领域JSON文件的 uncertainties 字段读取所有不确定性（不仅仅是已解决的）。

        Returns:
            List of uncertainty dictionaries (原始格式，包含所有字段)
        """
        try:
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")

            # ✨ 从领域JSON文件读取
            domain_file = Path(schema_path) / connection_name / "domains" / f"{domain_name}.json"
            if not domain_file.exists():
                logger.warning(f"领域文件 {domain_file} 不存在")
                return []

            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            # 返回所有不确定性（原样）
            uncertainties = domain_data.get("uncertainties", [])
            return uncertainties

        except Exception as e:
            logger.warning(f"Failed to load uncertainty data for {domain_name}: {e}")
            return []

    def _load_high_priority_rules(self, connection_name: str, domain_name: str) -> str:
        """
        加载领域的所有不确定性数据（原样格式化为文本，用于Prompt注入）。

        ✨ 新需求：将所有不确定性（包括所有优先级和状态）原样发送给模型，帮助AI：
        - 理解完整的业务上下文
        - 严格遵循已解决问题的用户答案
        - 参考未解决问题进行合理推断

        Args:
            connection_name: 数据库连接名
            domain_name: 业务域名称

        Returns:
            格式化的不确定性文本（按优先级分组，包含问题、状态、答案）
        """
        try:
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")

            # ✨ 新逻辑：从领域JSON文件中读取 uncertainties
            domain_file = Path(schema_path) / connection_name / "domains" / f"{domain_name}.json"
            if not domain_file.exists():
                logger.warning(f"领域文件 {domain_file} 不存在")
                return ""

            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            # ✨ 读取所有不确定性（不筛选，原样展示）
            uncertainties = domain_data.get("uncertainties", [])

            if not uncertainties:
                return ""

            # 格式化为结构化文本（原样展示所有不确定性）
            lines = []
            lines.append("# 该业务域的不确定性分析结果（构建本体时重要参考）")
            lines.append("")
            lines.append("以下是该领域的不确定性问题及用户确认的答案。")
            lines.append("构建本体时必须严格遵循已解决问题的答案！")
            lines.append("")

            # 按优先级分组
            by_priority = {"high": [], "medium": [], "low": []}
            for u in uncertainties:
                priority = u.get("priority", "low")
                by_priority[priority].append(u)

            # 先输出 high 优先级
            for priority in ["high", "medium", "low"]:
                items = by_priority[priority]
                if not items:
                    continue

                lines.append(f"## {priority.upper()} 优先级（{len(items)}个）")
                lines.append("")

                for idx, unc in enumerate(items, 1):
                    entity = unc.get("entity", "未知实体")
                    question = unc.get("question", "").strip()
                    answer = unc.get("answer", "").strip()
                    status = unc.get("status", "pending")
                    category = unc.get("category", "")

                    lines.append(f"### {idx}. [{entity}] {category or '未分类'}")
                    lines.append(f"**问题**: {question}")
                    lines.append(f"**状态**: {status}")

                    if answer:
                        lines.append(f"**✅ 用户确认**: {answer}")
                    else:
                        lines.append(f"**⚠️ 待确认**: 构建时可根据最佳实践推断")

                    lines.append("")

            result_text = "\n".join(lines)
            return result_text

        except Exception as e:
            logger.warning(f"Failed to load uncertainty rules for {domain_name}: {e}")
            return ""

    def _merge_domain_ontologies_simple(
        self,
        domain_ontologies: Dict[str, Dict[str, Any]],
        connection_name: str,
        database: str,
        model_manager
    ) -> Dict[str, Any]:
        """
        轻量级合并所有域的本体（无需 AI）。

        直接合并所有域的 concepts/properties/relationships。
        """
        all_concepts = {}
        all_properties = {}
        all_relationships = []
        all_hierarchies = []
        all_domain_insights = []
        all_uncertainties = []

        for domain_name, ont in domain_ontologies.items():
            all_concepts.update(ont.get("concepts", {}))
            all_properties.update(ont.get("properties", {}))
            all_relationships.extend(ont.get("relationships", []))
            all_hierarchies.extend(ont.get("hierarchies", []))
            if ont.get("domain_insights"):
                all_domain_insights.append(ont["domain_insights"])

            # 收集不确定性数据
            all_uncertainties.extend(ont.get("uncertainties", []))

        # 合并 domain insights
        primary_domains = [d.get("primary_domain") for d in all_domain_insights if d.get("primary_domain")]
        business_scenarios = [d.get("business_scenario") for d in all_domain_insights if d.get("business_scenario")]

        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "created_by": "simplified_parallel",
                "model": model_manager.get_current_model_name(),
                "source_database": database,
                "source_connection": connection_name,
                "build_method": "domain_based_parallel",
                "total_domains": len(domain_ontologies)
            },
            "concepts": all_concepts,
            "properties": all_properties,
            "relationships": all_relationships,
            "hierarchies": all_hierarchies,
            "domain_insights": {
                "primary_domain": ", ".join(set(primary_domains)),
                "sub_domains": list(domain_ontologies.keys()),
                "business_scenario": " | ".join(business_scenarios[:3]),  # 前3个
                "architecture_pattern": "Multi-Domain ERP"
            },
            "uncertainties": all_uncertainties,
            "statistics": {
                "concept_count": len(all_concepts),
                "property_count": len(all_properties),
                "relationship_count": len(all_relationships),
                "hierarchy_count": len(all_hierarchies),
                "uncertainty_count": len(all_uncertainties)
            }
        }




class OntologySearchTool(KodeTool):
    """
    Search ontology for concepts, properties, and relationships.

    Supports semantic, exact, and fuzzy search.
    """

    name: str = "OntologySearch"
    description: str = """Search stored ontology for concepts, properties, and relationships.
    Supports semantic search (with embeddings), exact matching, and fuzzy search."""

    args_schema: Type[BaseModel] = OntologySearchInput
    requires_permission: bool = False

    def _run(
        self,
        ontology_path: str,
        query: str,
        search_type: str = "semantic",
        top_k: int = 5,
    ) -> str:
        """
        Search ontology.

        Args:
            ontology_path: Path to ontology storage
            query: Search query
            search_type: Type of search
            top_k: Number of results

        Returns:
            Search results as JSON
        """
        try:
            # Load latest ontology
            latest_path = Path(ontology_path) / "ontology_latest.json"

            if not latest_path.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"No ontology found at {ontology_path}",
                    },
                    indent=2,
                )

            with open(latest_path, "r", encoding="utf-8") as f:
                ontology_data = json.load(f)

            ontology = ontology_data.get("ontology", {})
            query_lower = query.lower()

            results = {"concepts": [], "properties": [], "relationships": []}

            # if search_type == "exact":
            #     # Exact match search
            #     results = self._semantic_search(ontology, query_lower)

            # elif search_type == "fuzzy":
            #     # Fuzzy match search
            #     results = self._semantic_search(ontology, query_lower, top_k)

            # elif search_type == "semantic":
                # Semantic search with embeddings (ChromaDB)
            results = self._semantic_search(ontology, query, top_k, ontology_path)

            # 提取 uncertainties（完整列表）
            uncertainties = ontology.get("uncertainties", [])

            # 筛选与查询相关的不确定性（基于 entity 和 question）
            related_uncertainties = []
            unrelated_uncertainties = []

            query_lower = query.lower()
            for uncertainty in uncertainties:
                entity = uncertainty.get("entity", "").lower()
                question = uncertainty.get("question", "").lower()
                context = uncertainty.get("context", "").lower()

                # 判断是否相关（实体名匹配 OR 问题描述包含查询词）
                is_related = (
                    entity in query_lower or
                    query_lower in entity or
                    query_lower in question or
                    query_lower in context
                )

                if is_related:
                    related_uncertainties.append(uncertainty)
                else:
                    unrelated_uncertainties.append(uncertainty)

            # Return lightweight summary (save tokens)
            return json.dumps(
                {
                    "status": "success",
                    "query": query,
                    "search_type": search_type,
                    "results": results,  # Keep search results (usually small)
                    "ontology_version": ontology_data.get("version"),
                    "uncertainties": {
                        "related_count": len(related_uncertainties),
                        "unresolved_count": len([u for u in uncertainties if u.get("status") != "resolved"]),
                        "total_count": len(uncertainties),
                        "resolved_count": len([u for u in uncertainties if u.get("status") == "resolved"]),
                        "message": "Use FileRead to view full uncertainties from ontology_latest.json if needed"
                    }
                },
                indent=2,
                ensure_ascii=False,
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to search ontology: {str(e)}",
                },
                indent=2,
            )

    def _exact_search(self, ontology: Dict[str, Any], query: str) -> Dict[str, List]:
        """Exact match search."""
        results: Dict[str, List] = {"concepts": [], "properties": [], "relationships": []}

        # Search concepts
        for concept_name, concept_data in ontology.get("concepts", {}).items():
            if query in concept_name.lower() or query in concept_data.get(
                "business_name", ""
            ).lower():
                results["concepts"].append(concept_data)

        # Search properties
        for prop_key, prop_data in ontology.get("properties", {}).items():
            if query in prop_key.lower() or query in prop_data.get("business_name", "").lower():
                results["properties"].append(prop_data)

        return results

    def _fuzzy_search(
        self, ontology: Dict[str, Any], query: str, top_k: int
    ) -> Dict[str, List]:
        """Fuzzy match search with scoring."""
        results: Dict[str, List] = {"concepts": [], "properties": [], "relationships": []}

        # Simple fuzzy matching based on substring and word matching
        concept_scores = []
        for concept_name, concept_data in ontology.get("concepts", {}).items():
            # Search in multiple fields: technical name, business names (CN/EN), description
            search_targets = [
                concept_name,
                concept_data.get("business_name_cn", ""),
                concept_data.get("business_name_en", ""),
                concept_data.get("description", ""),
                concept_data.get("domain", "")
            ]
            score = self._calculate_fuzzy_score(query, search_targets)
            if score > 0:
                concept_scores.append((score, concept_data))

        # Sort by score and take top_k
        concept_scores.sort(reverse=True, key=lambda x: x[0])
        results["concepts"] = [item[1] for item in concept_scores[:top_k]]

        # Similar for properties
        property_scores = []
        for prop_key, prop_data in ontology.get("properties", {}).items():
            # Search in multiple fields
            search_targets = [
                prop_key,
                prop_data.get("business_name_cn", ""),
                prop_data.get("business_name_en", ""),
                prop_data.get("description", ""),
                prop_data.get("domain", "")
            ]
            score = self._calculate_fuzzy_score(query, search_targets)
            if score > 0:
                property_scores.append((score, prop_data))

        property_scores.sort(reverse=True, key=lambda x: x[0])
        results["properties"] = [item[1] for item in property_scores[:top_k]]

        return results

    def _calculate_fuzzy_score(self, query: str, targets: List[str]) -> float:
        """
        Calculate fuzzy match score with support for multi-keyword queries.

        Supports both English word matching and Chinese substring matching.
        """
        score = 0.0
        query_lower = query.lower()

        # Split query into words (for English) and keep original for Chinese char matching
        query_words = set(query_lower.split())

        for target in targets:
            if not target:
                continue

            target_lower = target.lower()

            # Strategy 1: Exact match (highest priority)
            if query_lower == target_lower:
                score += 100.0
                continue

            # Strategy 2: Full substring match (high priority)
            if query_lower in target_lower:
                score += 50.0
                continue

            # Strategy 3: Word/token overlap (for multi-keyword queries)
            target_words = set(target_lower.split())
            word_overlap = len(query_words & target_words)
            if word_overlap > 0:
                # Score proportional to overlap ratio
                score += word_overlap * 10.0

            # Strategy 4: Bidirectional substring matching (支持中文复合词匹配)
            # Check if query words contain target OR target contains query words
            for query_word in query_words:
                # 查询词包含目标 (e.g., "订单金额" contains "订单")
                if query_word in target_lower:
                    score += 15.0
                # 目标包含查询词 (e.g., "订单" in "订单金额")
                elif target_lower in query_word:
                    score += 12.0

        return score

    def _semantic_search(
        self, ontology: Dict[str, Any], query: str, top_k: int, ontology_path: str
    ) -> Dict[str, List]:
        """
        Semantic search using ChromaDB vector embeddings.

        Args:
            ontology: Ontology data structure
            query: Search query
            top_k: Number of results to return
            ontology_path: Path to ontology storage (used for ChromaDB persistence)

        Returns:
            Dictionary with concepts and properties matching the query
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.warning("ChromaDB not installed, falling back to fuzzy search")
            return self._fuzzy_search(ontology, query.lower(), top_k)

        try:
            # Initialize ChromaDB client with persistence
            chroma_dir = Path(ontology_path) / ".chroma"
            chroma_dir.mkdir(exist_ok=True)

            client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collections for concepts and properties
            concepts_collection = client.get_or_create_collection(
                name="ontology_concepts",
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )

            properties_collection = client.get_or_create_collection(
                name="ontology_properties",
                metadata={"hnsw:space": "cosine"}
            )

            # Check if we need to index (collection is empty)
            if concepts_collection.count() == 0:
                self._index_ontology_to_chroma(
                    ontology, concepts_collection, properties_collection
                )

            # Search concepts
            concept_count = concepts_collection.count()
            concept_results = None
            if concept_count > 0:
                concept_results = concepts_collection.query(
                    query_texts=[query],
                    n_results=min(top_k, concept_count)
                )

            # Search properties
            property_count = properties_collection.count()
            property_results = None
            if property_count > 0:
                property_results = properties_collection.query(
                    query_texts=[query],
                    n_results=min(top_k, property_count)
                )

            # Parse results and retrieve full ontology data
            results: Dict[str, List] = {"concepts": [], "properties": [], "relationships": []}

            # Add concepts
            if concept_results and concept_results["ids"] and concept_results["ids"][0]:
                for concept_id in concept_results["ids"][0]:
                    if concept_id in ontology.get("concepts", {}):
                        results["concepts"].append(ontology["concepts"][concept_id])

            # Add properties
            if property_results and property_results["ids"] and property_results["ids"][0]:
                for prop_id in property_results["ids"][0]:
                    if prop_id in ontology.get("properties", {}):
                        results["properties"].append(ontology["properties"][prop_id])

            return results

        except Exception as e:
            logger.warning(f"Semantic search failed: {e}, falling back to fuzzy search")
            return self._fuzzy_search(ontology, query.lower(), top_k)

    def _index_ontology_to_chroma(
        self,
        ontology: Dict[str, Any],
        concepts_collection,
        properties_collection
    ):
        """
        Index ontology data into ChromaDB collections.

        Args:
            ontology: Ontology data structure
            concepts_collection: ChromaDB collection for concepts
            properties_collection: ChromaDB collection for properties
        """
        # Index concepts
        concept_ids = []
        concept_docs = []
        concept_metadatas = []

        for concept_name, concept_data in ontology.get("concepts", {}).items():
            concept_ids.append(concept_name)

            # Create rich text representation for embedding
            doc_text = f"{concept_data.get('business_name_cn', '')} {concept_data.get('business_name_en', '')} {concept_data.get('description', '')} {concept_data.get('domain', '')}"
            concept_docs.append(doc_text)

            concept_metadatas.append({
                "technical_name": concept_name,
                "business_name": concept_data.get("business_name_cn", ""),
                "domain": concept_data.get("domain", "")
            })

        if concept_ids:
            concepts_collection.add(
                ids=concept_ids,
                documents=concept_docs,
                metadatas=concept_metadatas
            )

        # Index properties
        property_ids = []
        property_docs = []
        property_metadatas = []

        for prop_key, prop_data in ontology.get("properties", {}).items():
            property_ids.append(prop_key)

            # Create rich text representation
            doc_text = f"{prop_data.get('business_name_cn', '')} {prop_data.get('business_name_en', '')} {prop_data.get('description', '')} {prop_data.get('domain', '')}"
            property_docs.append(doc_text)

            property_metadatas.append({
                "property_key": prop_key,
                "business_name": prop_data.get("business_name_cn", ""),
                "domain": prop_data.get("domain", "")
            })

        if property_ids:
            properties_collection.add(
                ids=property_ids,
                documents=property_docs,
                metadatas=property_metadatas
            )

        logger.info(f"Indexed {len(concept_ids)} concepts and {len(property_ids)} properties to ChromaDB")


