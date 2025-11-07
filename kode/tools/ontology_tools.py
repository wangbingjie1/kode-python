"""Ontology building and storage tools for database schema understanding."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from kode.tools.base import KodeTool
from kode.core.model_manager import ModelManager
from kode.utils.config import ConfigManager


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


class OntologyStorageInput(BaseModel):
    """Input schema for OntologyStorageTool."""

    ontology: Dict[str, Any] = Field(description="Ontology data to store")
    storage_path: str = Field(
        default="./ontology_store", description="Path to store ontology files"
    )
    version: str = Field(default="v1.0", description="Ontology version identifier")
    format: str = Field(default="json", description="Storage format: json, rdf, owl")


class OntologySearchInput(BaseModel):
    """Input schema for OntologySearchTool."""

    ontology_path: str = Field(description="Path to ontology storage")
    query: str = Field(description="Search query (natural language)")
    search_type: str = Field(
        default="semantic", description="Search type: semantic, exact, fuzzy"
    )
    top_k: int = Field(default=5, description="Number of results to return")


class OntologyLoadInput(BaseModel):
    """Input schema for OntologyLoadTool."""

    connection_name: str = Field(description="Connection name to load ontology for")
    version: str = Field(default="latest", description="Version to load (latest or specific version)")


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

            # Load schema data
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            # Unwrap schema if it has version wrapper
            if "schema" in schema_data and isinstance(schema_data["schema"], dict):
                schema_metadata = schema_data["schema"]
            else:
                schema_metadata = schema_data

            # 核心改变：直接使用 AI 生成完整的本体，而不是传统代码转换
            ontology = self._build_ontology_with_ai(schema_metadata, connection_name)

            # Auto-save ontology to file
            if auto_save:
                save_result = self._save_ontology(ontology, connection_name, version)
                ontology["storage"] = save_result

            return json.dumps(
                {"status": "success", "ontology": ontology}, indent=2, ensure_ascii=False
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to build ontology: {str(e)}",
                },
                indent=2,
            )

    def _build_ontology_with_ai(
        self, schema_metadata: Dict[str, Any], connection_name: str
    ) -> Dict[str, Any]:
        """
        使用 AI 直接从数据库 schema 生成完整的业务本体。

        这是核心方法，完全由 AI 理解业务语义并生成本体，而非规则代码。
        """
        try:
            # 准备 schema 的紧凑表示
            schema_summary = self._prepare_schema_for_ai(schema_metadata)

            # 创建 AI prompt
            prompt = self._create_ontology_generation_prompt(schema_summary)

            # 调用 AI 模型
            config_manager = ConfigManager()
            config = config_manager.get_all()
            model_manager = ModelManager(config)
            model = model_manager.get_model("main")  # 使用 main 模型，这个任务很重要

            from langchain_core.messages import HumanMessage
            response = model.invoke([HumanMessage(content=prompt)])
            ai_output = response.content

            # 解析 AI 返回的 JSON
            ontology_data = self._extract_json_from_text(ai_output)

            if not ontology_data:
                raise ValueError("AI 未返回有效的 JSON 格式本体数据")

            # 添加元数据
            ontology = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": "ai",
                    "model": model_manager.get_current_model_name(),
                    "source_database": schema_metadata.get("database"),
                    "source_connection": connection_name,
                    "table_count": schema_metadata.get("table_count", 0),
                },
                "concepts": ontology_data.get("concepts", {}),
                "properties": ontology_data.get("properties", {}),
                "relationships": ontology_data.get("relationships", []),
                "hierarchies": ontology_data.get("hierarchies", []),
                "domain_insights": ontology_data.get("domain_insights", {}),
                "business_rules": ontology_data.get("business_rules", []),
                "recommendations": ontology_data.get("recommendations", []),
                "statistics": {
                    "concept_count": len(ontology_data.get("concepts", {})),
                    "property_count": len(ontology_data.get("properties", {})),
                    "relationship_count": len(ontology_data.get("relationships", [])),
                    "hierarchy_count": len(ontology_data.get("hierarchies", [])),
                },
            }

            return ontology

        except Exception as e:
            # Fallback: 返回基本结构
            return {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": "error_fallback",
                    "error": str(e),
                },
                "concepts": {},
                "properties": {},
                "relationships": [],
                "hierarchies": [],
            }

    def _prepare_schema_for_ai(self, schema_metadata: Dict[str, Any]) -> str:
        """
        将数据库 schema 转换为紧凑的、AI 友好的格式。

        包含：表名、列信息（名称、类型、注释）、主键、外键关系。
        """
        tables = schema_metadata.get("tables", {})
        relationships = schema_metadata.get("relationships", [])

        lines = []
        lines.append(f"数据库: {schema_metadata.get('database', '未知')}")
        lines.append(f"表数量: {len(tables)}")
        lines.append("")

        # 表和列信息
        for table_name, table_data in tables.items():
            lines.append(f"## {table_name}")

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
                lines.append(col_info)

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

    def _create_ontology_generation_prompt(self, schema_summary: str) -> str:
        """创建用于本体生成的 AI prompt。"""
        return f"""你是一位资深的 ERP 系统架构师和业务分析专家。请分析以下数据库 schema，构建一个完整的业务本体（Ontology）。

# 数据库 Schema

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

2. **Properties（属性）**: 每个字段的业务含义
   - technical_name: 技术名称（表名.字段名）
   - business_name_cn: 中文业务名称
   - business_name_en: 英文业务名称
   - description: 业务含义描述
   - data_type: 数据类型
   - nullable: 是否可空
   - concept: 所属概念（表名）

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

7. **Recommendations（建议）**: 基于 schema 的优化建议

# 输出格式

请严格按照以下 JSON 格式输出，不要有任何多余的解释：

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
      "primary_key": ["id"]
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
      "concept": "table_name"
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
  "business_rules": [
    "用户邮箱必须唯一",
    "订单必须关联有效用户",
    "商品价格不能为负"
  ],
  "recommendations": [
    "建议为订单表添加状态字段",
    "考虑添加用户行为日志表"
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
"""

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从 AI 输出中提取 JSON（可能包含 markdown 代码块）。"""
        import re

        # 尝试从 markdown 代码块中提取
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue

        # 尝试直接解析整个文本
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试查找第一个完整的 JSON 对象
        json_object_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_object_pattern, text, re.DOTALL)

        for match in matches:
            try:
                parsed = json.loads(match)
                # 检查是否包含必要的键
                if "concepts" in parsed or "properties" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

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

            # Update latest pointer
            latest_file = conn_dir / "ontology_latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(ontology_with_meta, f, indent=2, ensure_ascii=False)

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


class OntologyStorageTool(KodeTool):
    """
    Store and version ontology models.

    Supports multiple storage formats and versioning.
    """

    name: str = "OntologyStorage"
    description: str = """Store ontology to persistent storage with versioning.
    Supports JSON, RDF, and OWL formats. Creates versioned snapshots."""

    args_schema: Type[BaseModel] = OntologyStorageInput
    requires_permission: bool = True

    def _run(
        self,
        ontology: Dict[str, Any],
        storage_path: str = "./ontology_store",
        version: str = "v1.0",
        format: str = "json",
    ) -> str:
        """
        Store ontology.

        Args:
            ontology: Ontology data
            storage_path: Storage directory
            version: Version identifier
            format: Storage format

        Returns:
            Storage status message
        """
        try:
            storage_dir = Path(storage_path)
            storage_dir.mkdir(parents=True, exist_ok=True)

            # Add version metadata
            ontology_with_meta = {
                "version": version,
                "stored_at": datetime.now().isoformat(),
                "format": format,
                "ontology": ontology,
            }

            if format == "json":
                file_path = storage_dir / f"ontology_{version}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(ontology_with_meta, f, indent=2, ensure_ascii=False)

                # Also save latest version
                latest_path = storage_dir / "ontology_latest.json"
                with open(latest_path, "w", encoding="utf-8") as f:
                    json.dump(ontology_with_meta, f, indent=2, ensure_ascii=False)

                return json.dumps(
                    {
                        "status": "success",
                        "message": f"Ontology stored successfully",
                        "version": version,
                        "format": format,
                        "path": str(file_path),
                        "latest_path": str(latest_path),
                    },
                    indent=2,
                )

            elif format in ["rdf", "owl"]:
                return json.dumps(
                    {
                        "status": "warning",
                        "message": f"{format.upper()} format not yet implemented",
                        "suggestion": "Use JSON format for now",
                    },
                    indent=2,
                )

            else:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Unsupported format: {format}",
                    },
                    indent=2,
                )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to store ontology: {str(e)}",
                },
                indent=2,
            )


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

            if search_type == "exact":
                # Exact match search
                results = self._exact_search(ontology, query_lower)

            elif search_type == "fuzzy":
                # Fuzzy match search
                results = self._fuzzy_search(ontology, query_lower, top_k)

            elif search_type == "semantic":
                # TODO: Implement semantic search with embeddings
                return json.dumps(
                    {
                        "status": "warning",
                        "message": "Semantic search not yet implemented",
                        "suggestion": "Use 'exact' or 'fuzzy' search type",
                    },
                    indent=2,
                )

            return json.dumps(
                {
                    "status": "success",
                    "query": query,
                    "search_type": search_type,
                    "results": results,
                    "ontology_version": ontology_data.get("version"),
                },
                indent=2,
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
            score = self._calculate_fuzzy_score(
                query, [concept_name, concept_data.get("business_name", "")]
            )
            if score > 0:
                concept_scores.append((score, concept_data))

        # Sort by score and take top_k
        concept_scores.sort(reverse=True, key=lambda x: x[0])
        results["concepts"] = [item[1] for item in concept_scores[:top_k]]

        # Similar for properties
        property_scores = []
        for prop_key, prop_data in ontology.get("properties", {}).items():
            score = self._calculate_fuzzy_score(
                query, [prop_key, prop_data.get("business_name", "")]
            )
            if score > 0:
                property_scores.append((score, prop_data))

        property_scores.sort(reverse=True, key=lambda x: x[0])
        results["properties"] = [item[1] for item in property_scores[:top_k]]

        return results

    def _calculate_fuzzy_score(self, query: str, targets: List[str]) -> float:
        """Calculate simple fuzzy match score."""
        score = 0.0
        query_words = set(query.lower().split())

        for target in targets:
            if not target:
                continue

            target_lower = target.lower()

            # Exact match: highest score
            if query == target_lower:
                score += 10.0

            # Substring match
            elif query in target_lower:
                score += 5.0

            # Word overlap
            target_words = set(target_lower.split())
            overlap = len(query_words & target_words)
            if overlap > 0:
                score += overlap * 2.0

        return score


class OntologyLoadTool(KodeTool):
    """
    Load previously built ontology from storage.

    Use this tool to retrieve cached ontology instead of rebuilding.
    """

    name: str = "OntologyLoad"
    description: str = """Load previously built business ontology from storage.
    This is much faster than rebuilding ontology. Use this when you need ontology
    information and suspect it may have been built before."""

    args_schema: Type[BaseModel] = OntologyLoadInput
    requires_permission: bool = False

    def _run(self, connection_name: str, version: str = "latest") -> str:
        """
        Load ontology from storage.

        Args:
            connection_name: Connection name
            version: Version to load (latest or specific)

        Returns:
            Ontology data as JSON
        """
        try:
            config = ConfigManager()
            storage_path = config.get("storage.ontology_path", "./ontology_store")
            conn_dir = Path(storage_path) / connection_name

            if not conn_dir.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"No ontology found for connection '{connection_name}'",
                        "suggestion": "Use OntologyBuilder to build ontology first",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # Load specific version or latest
            if version == "latest":
                ontology_file = conn_dir / "ontology_latest.json"
            else:
                ontology_file = conn_dir / f"ontology_{version}.json"

            if not ontology_file.exists():
                # List available versions
                available = list(conn_dir.glob("ontology_v*.json"))
                available_versions = [f.stem.replace("ontology_", "") for f in available]

                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Ontology version '{version}' not found",
                        "available_versions": available_versions,
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            with open(ontology_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["loaded_from_cache"] = True
            data["loaded_at"] = datetime.now().isoformat()

            return json.dumps(data, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Failed to load ontology: {str(e)}",
                },
                indent=2,
            )
