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

    schema_metadata: Dict[str, Any] = Field(
        description="Database schema metadata from DatabaseSchemaExtractor"
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
    """

    name: str = "OntologyBuilder"
    description: str = """Build business ontology from database schema metadata.
    Converts tables to entities/concepts, columns to properties/attributes,
    and enriches with business semantics and inferred relationships."""

    args_schema: Type[BaseModel] = OntologyBuilderInput
    requires_permission: bool = False

    def _run(
        self,
        schema_metadata: Dict[str, Any],
        use_llm_enrichment: bool = False,
        add_business_terms: bool = True,
        infer_relationships: bool = True,
        extract_hierarchies: bool = True,
        auto_save: bool = True,
        version: str = "auto",
    ) -> str:
        """
        Build ontology from schema.

        Args:
            schema_metadata: Database schema from extractor
            use_llm_enrichment: Use LLM for enrichment
            add_business_terms: Convert to business terms
            infer_relationships: Infer implicit relationships
            extract_hierarchies: Extract hierarchies

        Returns:
            Ontology as JSON
        """
        try:
            ontology = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "source_database": schema_metadata.get("database"),
                    "source_connection": schema_metadata.get("connection", {}).get("name"),
                    "table_count": schema_metadata.get("table_count", 0),
                },
                "concepts": {},
                "properties": {},
                "relationships": [],
                "hierarchies": [],
            }

            tables = schema_metadata.get("tables", {})

            # Convert tables to concepts
            for table_name, table_data in tables.items():
                concept = self._table_to_concept(table_name, table_data, add_business_terms)
                ontology["concepts"][table_name] = concept

                # Extract properties from columns
                if "columns" in table_data:
                    for column in table_data["columns"]:
                        prop = self._column_to_property(
                            table_name, column, add_business_terms
                        )
                        prop_key = f"{table_name}.{column['name']}"
                        ontology["properties"][prop_key] = prop

            # Extract explicit relationships from FK constraints
            if "relationships" in schema_metadata:
                for rel in schema_metadata["relationships"]:
                    relationship = self._fk_to_relationship(rel)
                    ontology["relationships"].append(relationship)

            # Infer additional relationships
            if infer_relationships:
                inferred = self._infer_relationships(tables)
                ontology["relationships"].extend(inferred)

            # Extract hierarchies
            if extract_hierarchies:
                hierarchies = self._extract_hierarchies(tables, ontology["relationships"])
                ontology["hierarchies"] = hierarchies

            # LLM enrichment
            if use_llm_enrichment:
                try:
                    ontology = self._enrich_with_llm(ontology, schema_metadata)
                    ontology["enrichment_status"] = "completed"
                except Exception as e:
                    ontology["enrichment_status"] = f"failed: {str(e)}"

            # Add statistics
            ontology["statistics"] = {
                "concept_count": len(ontology["concepts"]),
                "property_count": len(ontology["properties"]),
                "relationship_count": len(ontology["relationships"]),
                "hierarchy_count": len(ontology["hierarchies"]),
            }

            # Auto-save ontology to file
            if auto_save:
                connection_name = schema_metadata.get("connection", {}).get("name", "unknown")
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

    def _table_to_concept(
        self, table_name: str, table_data: Dict[str, Any], add_business_terms: bool
    ) -> Dict[str, Any]:
        """Convert database table to ontology concept."""
        concept = {
            "name": table_name,
            "type": "entity",
            "source": "database_table",
            "column_count": table_data.get("column_count", 0),
        }

        # Add business name (convert snake_case to Title Case)
        if add_business_terms:
            business_name = " ".join(word.capitalize() for word in table_name.split("_"))
            concept["business_name"] = business_name

        # Add primary key information
        if "primary_key" in table_data:
            concept["primary_key"] = table_data["primary_key"]["columns"]

        return concept

    def _column_to_property(
        self, table_name: str, column: Dict[str, Any], add_business_terms: bool
    ) -> Dict[str, Any]:
        """Convert database column to ontology property."""
        prop = {
            "name": column["name"],
            "concept": table_name,
            "data_type": column["type"],
            "nullable": column.get("nullable", True),
            "autoincrement": column.get("autoincrement", False),
        }

        # Add business name
        if add_business_terms:
            business_name = " ".join(word.capitalize() for word in column["name"].split("_"))
            prop["business_name"] = business_name

        # Add default value if present
        if column.get("default"):
            prop["default_value"] = column["default"]

        return prop

    def _fk_to_relationship(self, fk: Dict[str, Any]) -> Dict[str, Any]:
        """Convert foreign key to ontology relationship."""
        return {
            "type": "foreign_key",
            "from_concept": fk["from_table"],
            "to_concept": fk["to_table"],
            "from_properties": fk["from_columns"],
            "to_properties": fk["to_columns"],
            "constraint_name": fk.get("constraint_name"),
            "cardinality": "many-to-one",  # Default FK cardinality
        }

    def _infer_relationships(self, tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Infer additional relationships beyond explicit FK constraints."""
        inferred = []

        # Look for common naming patterns that suggest relationships
        # E.g., "user_id" column might relate to "users" table
        for table_name, table_data in tables.items():
            if "columns" not in table_data:
                continue

            for column in table_data["columns"]:
                col_name = column["name"].lower()

                # Pattern: column ends with "_id"
                if col_name.endswith("_id"):
                    potential_table = col_name[:-3]  # Remove "_id"

                    # Try plural form
                    potential_tables = [
                        potential_table,
                        potential_table + "s",
                        potential_table + "es",
                    ]

                    for pot_table in potential_tables:
                        if pot_table in tables and pot_table != table_name:
                            inferred.append(
                                {
                                    "type": "inferred",
                                    "from_concept": table_name,
                                    "to_concept": pot_table,
                                    "from_properties": [col_name],
                                    "to_properties": ["id"],
                                    "inference_reason": "naming_pattern",
                                    "cardinality": "many-to-one",
                                }
                            )
                            break

        return inferred

    def _extract_hierarchies(
        self, tables: Dict[str, Any], relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract hierarchical relationships (e.g., parent-child).

        Detects hierarchies through:
        1. Self-referencing foreign keys
        2. Standard hierarchy column patterns (parent_id, pid, etc.)
        3. Level/depth indicators
        4. Category/classification structures
        5. Order/sequence fields suggesting tree structures
        """
        hierarchies = []

        # 1. Self-referencing relationships (explicit hierarchies)
        for rel in relationships:
            if rel["from_concept"] == rel["to_concept"]:
                hierarchies.append(
                    {
                        "type": "self_referencing",
                        "concept": rel["from_concept"],
                        "parent_property": rel["to_properties"][0]
                        if rel["to_properties"]
                        else None,
                        "child_property": rel["from_properties"][0]
                        if rel["from_properties"]
                        else None,
                        "description": f"自引用关系: {rel['from_concept']} 表具有树形结构",
                    }
                )

        # 2. Standard hierarchy column patterns
        hierarchy_indicators = [
            "parent_id",
            "parent",
            "pid",  # Common abbreviation
            "superior_id",
            "manager_id",
            "category_id",
            "parent_code",
            "up_id",  # Some systems use this
        ]

        for table_name, table_data in tables.items():
            if "columns" not in table_data:
                continue

            columns = table_data["columns"]
            col_names = [col["name"].lower() for col in columns]

            # Check for standard indicators
            for col in columns:
                col_name = col["name"].lower()
                if col_name in hierarchy_indicators:
                    hierarchies.append(
                        {
                            "type": "parent_child",
                            "concept": table_name,
                            "parent_property": col_name,
                            "description": f"{table_name} 通过 {col_name} 字段形成层次结构",
                        }
                    )

            # 3. Detect level/depth indicators (multi-level structures)
            level_indicators = ["level", "depth", "tier", "rank", "grade"]
            has_level = any(
                any(indicator in col_name for indicator in level_indicators)
                for col_name in col_names
            )

            if has_level:
                level_col = next(
                    col["name"]
                    for col in columns
                    if any(indicator in col["name"].lower() for indicator in level_indicators)
                )
                hierarchies.append(
                    {
                        "type": "level_based",
                        "concept": table_name,
                        "level_property": level_col,
                        "description": f"{table_name} 使用 {level_col} 字段表示层级深度",
                    }
                )

            # 4. Category/Classification structures
            is_category_table = any(
                keyword in table_name.lower()
                for keyword in ["category", "class", "type", "group", "tag"]
            )

            if is_category_table:
                # Check if has parent reference or level
                has_parent = any(
                    "parent" in col_name or "pid" == col_name for col_name in col_names
                )
                if has_parent:
                    parent_col = next(
                        col["name"]
                        for col in columns
                        if "parent" in col["name"].lower() or col["name"].lower() == "pid"
                    )
                    hierarchies.append(
                        {
                            "type": "category_hierarchy",
                            "concept": table_name,
                            "parent_property": parent_col,
                            "description": f"{table_name} 是分类表,通过 {parent_col} 形成层次",
                        }
                    )

            # 5. Tree structure indicators (path, lft/rgt for nested sets)
            has_tree_path = any("path" in col_name for col_name in col_names)
            has_nested_set = "lft" in col_names and "rgt" in col_names

            if has_tree_path:
                path_col = next(col["name"] for col in columns if "path" in col["name"].lower())
                hierarchies.append(
                    {
                        "type": "path_based",
                        "concept": table_name,
                        "path_property": path_col,
                        "description": f"{table_name} 使用路径字段 {path_col} 存储层次结构",
                    }
                )

            if has_nested_set:
                hierarchies.append(
                    {
                        "type": "nested_set",
                        "concept": table_name,
                        "left_property": "lft",
                        "right_property": "rgt",
                        "description": f"{table_name} 使用嵌套集合模型(Nested Set)存储树形结构",
                    }
                )

            # 6. Adjacency patterns (common naming suggesting hierarchy)
            adjacency_patterns = [
                ("parent", "parent reference"),
                ("superior", "superior relationship"),
                ("belongs_to", "belonging hierarchy"),
            ]

            for pattern, desc in adjacency_patterns:
                matching_cols = [col for col in columns if pattern in col["name"].lower()]
                for col in matching_cols:
                    if col["name"].lower() not in hierarchy_indicators:  # Avoid duplicates
                        hierarchies.append(
                            {
                                "type": "adjacency_list",
                                "concept": table_name,
                                "reference_property": col["name"],
                                "description": f"{table_name}.{col['name']} 可能表示层次关系 ({desc})",
                            }
                        )

        # Remove duplicates (same concept + type)
        seen = set()
        unique_hierarchies = []
        for h in hierarchies:
            key = (h["concept"], h["type"])
            if key not in seen:
                seen.add(key)
                unique_hierarchies.append(h)

        return unique_hierarchies

    def _enrich_with_llm(
        self, ontology: Dict[str, Any], schema_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to enrich ontology with business semantics.

        This method uses a language model to:
        1. Generate meaningful business descriptions for entities
        2. Translate technical names to business terms
        3. Infer implicit business rules
        4. Identify domain-specific patterns
        5. Add Chinese business names and descriptions

        Args:
            ontology: Base ontology from rule-based extraction
            schema_metadata: Original database schema

        Returns:
            Enriched ontology with LLM-generated insights
        """
        try:
            # Get LLM instance
            config_manager = ConfigManager()
            config = config_manager.get_all()
            model_manager = ModelManager(config)
            model = model_manager.get_model("quick")  # Use quick model for enrichment

            # Prepare context for LLM
            concepts_summary = self._prepare_concepts_summary(ontology)
            relationships_summary = self._prepare_relationships_summary(ontology)

            # Create enrichment prompt
            prompt = self._create_enrichment_prompt(
                concepts_summary, relationships_summary, schema_metadata
            )

            # Call LLM
            from langchain_core.messages import HumanMessage

            response = model.invoke([HumanMessage(content=prompt)])
            llm_output = response.content

            # Parse LLM response and apply enrichments
            enriched_ontology = self._apply_llm_enrichments(ontology, llm_output)

            return enriched_ontology

        except Exception as e:
            # If LLM enrichment fails, return original ontology
            ontology["enrichment_error"] = str(e)
            return ontology

    def _prepare_concepts_summary(self, ontology: Dict[str, Any]) -> str:
        """Prepare a summary of concepts for LLM context."""
        concepts = ontology.get("concepts", {})
        summary_lines = []

        for concept_name, concept_data in list(concepts.items())[:20]:  # Limit to 20
            summary_lines.append(
                f"- {concept_name}: {concept_data.get('business_name', 'N/A')} "
                f"({concept_data.get('column_count', 0)} columns)"
            )

        return "\n".join(summary_lines)

    def _prepare_relationships_summary(self, ontology: Dict[str, Any]) -> str:
        """Prepare a summary of relationships for LLM context."""
        relationships = ontology.get("relationships", [])
        summary_lines = []

        for rel in relationships[:15]:  # Limit to 15
            summary_lines.append(
                f"- {rel['from_concept']} → {rel['to_concept']} "
                f"({rel.get('type', 'unknown')})"
            )

        return "\n".join(summary_lines)

    def _create_enrichment_prompt(
        self,
        concepts_summary: str,
        relationships_summary: str,
        schema_metadata: Dict[str, Any],
    ) -> str:
        """Create prompt for LLM enrichment."""
        database_name = schema_metadata.get("database", "未知数据库")
        table_count = schema_metadata.get("table_count", 0)

        prompt = f"""你是一位资深的业务分析师和数据架构师。请分析以下数据库结构，为其构建业务本体。

# 数据库信息
- 数据库名称: {database_name}
- 表数量: {table_count}

# 当前实体（部分）
{concepts_summary}

# 当前关系（部分）
{relationships_summary}

# 任务
请为每个实体提供以下信息（JSON 格式）：

1. **业务名称（中文）**: 准确的业务术语
2. **业务描述**: 清晰的业务含义（50字以内）
3. **领域分类**: 所属业务领域（如：用户管理、订单管理、财务等）
4. **重要性**: high/medium/low

请以 JSON 格式返回，格式如下：

```json
{{
  "entities": [
    {{
      "technical_name": "users",
      "business_name_cn": "用户",
      "business_description": "系统注册用户，包含个人信息和账户状态",
      "domain": "用户管理",
      "importance": "high",
      "business_rules": ["用户名唯一", "必须验证邮箱"]
    }},
    ...
  ],
  "domain_insights": {{
    "primary_domain": "电商平台",
    "sub_domains": ["用户管理", "订单管理", "商品管理"],
    "architecture_pattern": "微服务/单体应用"
  }},
  "recommendations": [
    "建议添加用户行为日志表",
    "订单表应该增加状态机字段"
  ]
}}
```

只返回 JSON，不要有其他解释。"""

        return prompt

    def _apply_llm_enrichments(
        self, ontology: Dict[str, Any], llm_output: str
    ) -> Dict[str, Any]:
        """Apply LLM-generated enrichments to ontology."""
        try:
            # Extract JSON from LLM output
            llm_json = self._extract_json_from_text(llm_output)

            if not llm_json:
                return ontology

            # Apply entity enrichments
            entities = llm_json.get("entities", [])
            for entity_info in entities:
                tech_name = entity_info.get("technical_name")
                if tech_name in ontology["concepts"]:
                    concept = ontology["concepts"][tech_name]
                    concept["business_name_cn"] = entity_info.get("business_name_cn")
                    concept["business_description"] = entity_info.get(
                        "business_description"
                    )
                    concept["domain"] = entity_info.get("domain")
                    concept["importance"] = entity_info.get("importance", "medium")
                    concept["business_rules"] = entity_info.get("business_rules", [])

            # Add domain insights
            if "domain_insights" in llm_json:
                ontology["domain_insights"] = llm_json["domain_insights"]

            # Add recommendations
            if "recommendations" in llm_json:
                ontology["recommendations"] = llm_json["recommendations"]

            ontology["llm_enriched"] = True

            return ontology

        except Exception as e:
            ontology["enrichment_parse_error"] = str(e)
            return ontology

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text that might contain markdown code blocks."""
        import re

        # Try to find JSON in markdown code blocks
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # Try to parse entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_object_pattern, text, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
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
