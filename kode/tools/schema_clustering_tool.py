"""Database schema clustering and domain partitioning tools."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from kode.core.model_manager import ModelManager
from kode.tools.base import KodeTool
from kode.utils.config import ConfigManager
from kode.utils.context import get_current_user_id
from kode.utils.path_utils import get_safe_connection_path


class DatabaseSchemaClustererInput(BaseModel):
    """Input schema for DatabaseSchemaClusterer."""

    connection_name: str = Field(description="Database connection name")
    schema_file: str = Field(
        description="Path to the raw schema JSON file (e.g., schema_store/yanfa/schema_latest.json)"
    )
    target_tables_per_domain: int = Field(
        default=10,
        description="Target number of tables per domain (AI will try to group accordingly, not a hard limit)"
    )
    max_columns_for_analysis: Optional[int] = Field(
        default=None,
        description="Max columns to send to AI for analysis (None = all columns, recommended: 20-30 for large tables)"
    )
    llm_model: str = Field(
        default="quick",
        description="LLM model pointer to use for clustering (quick/main/task)"
    )
    output_language: str = Field(
        default="en",
        description="Output language for domain names: 'en' for English, 'zh' for Chinese"
    )


class DatabaseSchemaClusterer(KodeTool):
    """
    Cluster database tables into business domains using AI-driven semantic analysis.

    This tool analyzes table names, column names, comments, and foreign key relationships
    to intelligently group related tables into cohesive business domains. The result is
    a multi-file schema storage structure optimized for AI context loading.

    Benefits:
    - Reduces AI context window usage (load only relevant domains)
    - Improves query performance (targeted schema loading)
    - Better semantic organization (business-aligned grouping)
    - Scalable for large databases (100+ tables)
    """

    name: str = "DatabaseSchemaClusterer"
    description: str = """Cluster database tables into business domains using AI semantic analysis.

    Analyzes table/column names, comments, and relationships to group related tables.
    Outputs domain-partitioned schema files for efficient AI loading.

    Example output structure:
    schema_store/yanfa/
      schema_raw.json          # Full backup
      domain_index.json        # Domain catalog
      domains/
        user_management.json   # 12 tables
        order_system.json      # 15 tables
        analytics.json         # 8 tables

    Use cases:
    - Large databases (50+ tables) with context overflow issues
    - Multi-module ERP systems
    - Microservice-oriented schemas
    """

    args_schema: Type[BaseModel] = DatabaseSchemaClustererInput
    requires_permission: bool = False  # Read-only analysis

    def _run(
        self,
        connection_name: str,
        schema_file: str,
        target_tables_per_domain: int = 10,
        max_columns_for_analysis: Optional[int] = None,
        llm_model: str = "quick",
        output_language: str = "en",
    ) -> str:
        """
        Execute schema clustering.

        Args:
            connection_name: Database connection name
            schema_file: Path to raw schema JSON
            target_tables_per_domain: Target tables per domain (not a hard limit)
            max_columns_for_analysis: Max columns to analyze (None = all)
            llm_model: Model pointer for clustering
            output_language: Domain name language ('en' or 'zh')

        Returns:
            Clustering result as JSON
        """
        from kode.utils.logger import setup_logger
        logger = setup_logger(__name__)

        try:
            # 1. Load raw schema
            schema_data = self._load_schema(schema_file)
            tables = schema_data["schema"]["tables"]
            original_table_count = len(tables)

            # 🔑 1.5 读取 business_context.json 中的排除配置
            exclusion_config = self._load_exclusion_config(connection_name)
            excluded_tables = exclusion_config.get("tables", [])
            excluded_prefixes = exclusion_config.get("prefixes", [])

            if excluded_tables:
                # 过滤掉排除的表
                tables = {k: v for k, v in tables.items() if k not in excluded_tables}
                logger.info(
                    f"[SchemaClusterer] 排除了 {len(excluded_tables)} 个冗余表"
                    + (f": {excluded_tables[:10]}..." if len(excluded_tables) > 10 else f": {excluded_tables}")
                )
                # 更新 schema_data 中的 tables
                schema_data["schema"]["tables"] = tables

            if excluded_prefixes:
                logger.info(f"[SchemaClusterer] 排除前缀: {excluded_prefixes}")

            total_tables = len(tables)

            # 2. Extract table features for AI analysis
            table_features = self._extract_table_features(
                tables, max_columns=max_columns_for_analysis
            )

            # 3. Calculate optimal domain count
            # Use target as a guide, but let AI decide the final grouping
            estimated_domains = max(1, total_tables // target_tables_per_domain)

            # 4. Use AI to cluster tables into domains
            domains = self._cluster_with_ai(
                table_features=table_features,
                estimated_domains=estimated_domains,
                target_tables_per_domain=target_tables_per_domain,
                llm_model=llm_model,
                output_language=output_language,
                excluded_prefixes=excluded_prefixes,  # 🔑 新增：传递排除前缀
            )

            # 5. Validate and adjust clustering result
            domains = self._validate_clustering(domains, list(tables.keys()))

            # 6. Save domain-partitioned schemas
            storage_result = self._save_domain_schemas(
                connection_name=connection_name,
                schema_data=schema_data,
                domains=domains,
            )

            # 7. Build summary
            summary = {
                "status": "success",
                "connection_name": connection_name,
                "clustering_summary": {
                    "original_table_count": original_table_count,
                    "excluded_table_count": len(excluded_tables) if excluded_tables else 0,
                    "excluded_tables": excluded_tables[:20] if excluded_tables else [],  # 最多显示20个
                    "excluded_prefixes": excluded_prefixes,  # 🔑 新增：显示排除前缀
                    "total_tables": total_tables,
                    "total_domains": len(domains),
                    "avg_tables_per_domain": total_tables / len(domains) if domains else 0,
                    "domains": [
                        {
                            "name": d["name"],
                            "table_count": len(d["tables"]),
                            "description": d.get("description", ""),
                        }
                        for d in domains
                    ],
                },
                "storage": storage_result,
                "message": (
                    f"Successfully clustered {total_tables} tables into {len(domains)} domains"
                    + (f" (excluded {len(excluded_tables)} tables with prefixes: {excluded_prefixes})" if excluded_tables else "")
                ),
            }

            return json.dumps(summary, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Schema clustering failed: {str(e)}",
                },
                indent=2,
            )

    def _load_schema(self, schema_file: str) -> Dict[str, Any]:
        """Load schema from JSON file."""
        schema_path = Path(schema_file)
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_exclusion_config(self, connection_name: str) -> Dict[str, Any]:
        """
        从 business_context.json 读取排除配置。

        Args:
            connection_name: 数据库连接名

        Returns:
            排除配置字典：
            {
                "tables": ["table1", "table2", ...],
                "prefixes": ["ao_", "candy_chat_", ...],
                "reasons": {"ao_*": "用户说 AO 开头是已下线功能", ...}
            }
        """
        config = ConfigManager()
        ontology_path = config.get("storage.ontology_path", "./ontology_store")
        # 🔑 修复：添加 user_id 隔离
        from kode.utils.context import get_current_user_id
        user_id = get_current_user_id()
        safe_conn_name = get_safe_connection_path(connection_name)
        context_file = Path(ontology_path) / user_id / safe_conn_name / "business_context.json"

        if not context_file.exists():
            return {"tables": [], "prefixes": [], "reasons": {}}

        try:
            with open(context_file, "r", encoding="utf-8") as f:
                context_data = json.load(f)
            return {
                "tables": context_data.get("excluded_tables", []),
                "prefixes": context_data.get("excluded_prefixes", []),
                "reasons": context_data.get("exclusion_reasons", {}),
            }
        except Exception:
            return {"tables": [], "prefixes": [], "reasons": {}}

    def _extract_table_features(
        self, tables: Dict[str, Any], max_columns: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract key features from tables for AI analysis.

        Args:
            tables: Dictionary of table metadata
            max_columns: Maximum columns to include (None = all)

        Returns:
            List of table features
        """
        features = []

        for table_name, table_data in tables.items():
            columns = table_data.get("columns", [])

            # Limit columns if specified
            if max_columns is not None and len(columns) > max_columns:
                # Take first N columns (usually most important)
                columns = columns[:max_columns]

            # Extract foreign key relationships
            related_tables = [
                fk["referred_table"]
                for fk in table_data.get("foreign_keys", [])
            ]

            feature = {
                "table_name": table_name,
                "table_comment": table_data.get("comment", ""),
                "column_count": table_data.get("column_count", len(columns)),
                "columns": [
                    {
                        "name": col["name"],
                        "type": col["type"],
                        "comment": col.get("comment", ""),
                    }
                    for col in columns
                ],
                "related_tables": related_tables,
                "has_primary_key": bool(table_data.get("primary_key")),
                "foreign_key_count": len(table_data.get("foreign_keys", [])),
            }
            features.append(feature)

        return features

    def _cluster_with_ai(
        self,
        table_features: List[Dict[str, Any]],
        estimated_domains: int,
        target_tables_per_domain: int,
        llm_model: str,
        output_language: str,
        excluded_prefixes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Use AI to cluster tables into business domains.

        Args:
            table_features: Extracted table features
            estimated_domains: Estimated number of domains
            target_tables_per_domain: Target tables per domain
            llm_model: Model pointer to use
            output_language: Output language code
            excluded_prefixes: 已排除的表前缀列表（这些表已被过滤，不需要分析）

        Returns:
            List of domain definitions
        """
        # Build prompt
        lang_instruction = (
            "Domain names MUST be in English (e.g., user_management, order_system, analytics)"
            if output_language == "en"
            else "领域名称必须使用中文（如：用户管理、订单系统、数据分析）"
        )

        # 🔑 如果有排除前缀，添加提示信息
        exclusion_note = ""
        if excluded_prefixes:
            exclusion_note = f"""
Note: The following table prefixes have been excluded from this analysis (they represent offline/deprecated systems):
- {', '.join(excluded_prefixes)}
These tables are already filtered out. Focus on grouping the remaining active tables.
"""

        prompt = f"""You are a database architect analyzing a database schema with {len(table_features)} tables.

Your task: Group these tables into approximately {estimated_domains} business domains based on semantic relationships.
{exclusion_note}
Guidelines:
1. Aim for {target_tables_per_domain} tables per domain (flexible, not a hard limit)
2. Group tables by business function (e.g., user management, order processing, analytics)
3. Consider table names, column names, comments, and foreign key relationships
4. Each domain should be cohesive and self-contained when possible
5. {lang_instruction}
6. Provide a brief description for each domain (1-2 sentences)

Table Information:
{json.dumps(table_features, ensure_ascii=False, indent=2)}

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "domains": [
    {{
      "name": "domain_identifier",
      "display_name": "Human Readable Name",
      "description": "Brief description of this domain's business purpose",
      "tables": ["table1", "table2", "table3"]
    }}
  ]
}}

IMPORTANT: Ensure ALL {len(table_features)} tables are assigned to exactly one domain. Do not omit any tables.
"""

        # Get model with config
        config = ConfigManager()
        model_manager = ModelManager(config._config)
        model = model_manager.get_model(llm_model)

        # Invoke AI
        response = model.invoke(prompt)

        # Extract content from response
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)

        # Parse JSON from response
        try:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)
            return result.get("domains", [])

        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON: {e}\nResponse: {response_text[:500]}")

    def _validate_clustering(
        self, domains: List[Dict[str, Any]], all_tables: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate clustering result and fix issues.

        Ensures:
        - All tables are assigned
        - No duplicate assignments
        - Domain names are valid identifiers

        Args:
            domains: Domain definitions from AI
            all_tables: Complete list of table names

        Returns:
            Validated and corrected domain definitions
        """
        # Track assigned tables
        assigned_tables = set()
        for domain in domains:
            assigned_tables.update(domain.get("tables", []))

        # Find missing tables
        missing_tables = set(all_tables) - assigned_tables

        # If there are missing tables, add them to an "other" domain
        if missing_tables:
            other_domain = {
                "name": "other",
                "display_name": "Other Tables",
                "description": "Tables that could not be clearly categorized",
                "tables": list(missing_tables),
            }
            domains.append(other_domain)

        # Remove duplicate table assignments (keep first occurrence)
        seen_tables = set()
        for domain in domains:
            unique_tables = []
            for table in domain.get("tables", []):
                if table not in seen_tables:
                    unique_tables.append(table)
                    seen_tables.add(table)
            domain["tables"] = unique_tables

        # Ensure domain names are valid identifiers
        for domain in domains:
            if "name" not in domain or not domain["name"]:
                # Generate name from display_name or use generic
                if "display_name" in domain:
                    domain["name"] = (
                        domain["display_name"]
                        .lower()
                        .replace(" ", "_")
                        .replace("-", "_")
                    )
                else:
                    domain["name"] = f"domain_{len(domains)}"

        return domains

    def _save_domain_schemas(
        self,
        connection_name: str,
        schema_data: Dict[str, Any],
        domains: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Save domain-partitioned schemas to disk.

        Creates structure:
        schema_store/{connection_name}/
          schema_raw.json          # Full backup
          domain_index.json        # Domain catalog
          domains/
            {domain_name}.json     # Per-domain schemas

        Args:
            connection_name: Database connection name
            schema_data: Complete schema data
            domains: Domain definitions

        Returns:
            Storage result metadata
        """
        try:
            config = ConfigManager()
            storage_path = config.get("storage.schema_path", "./schema_store")
            user_id = get_current_user_id()

            safe_conn_name = get_safe_connection_path(connection_name)
            base_dir = Path(storage_path) / user_id / safe_conn_name
            domains_dir = base_dir / "domains"
            domains_dir.mkdir(parents=True, exist_ok=True)

            all_tables = schema_data["schema"]["tables"]

            # Save raw schema as backup
            raw_file = base_dir / "schema_raw.json"
            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)

            # Save per-domain schemas
            domain_files = []
            for domain in domains:
                domain_name = domain["name"]
                domain_tables = domain["tables"]

                # Extract only relevant tables for this domain
                # Build tables dict with schema_ref
                tables_with_ref = {}
                for table_name in domain_tables:
                    if table_name in all_tables:
                        table_data = all_tables[table_name].copy()
                        # Add schema reference for precise lookup
                        table_data["schema_ref"] = {
                            "connection": connection_name,
                            "table": table_name,
                            "schema_file": str(raw_file),
                            "json_path": f"schema.tables.{table_name}"
                        }
                        tables_with_ref[table_name] = table_data

                domain_schema = {
                    "domain_name": domain_name,
                    "display_name": domain.get("display_name", domain_name),
                    "description": domain.get("description", ""),
                    "table_count": len(domain_tables),
                    "created_at": datetime.now().isoformat(),
                    "connection": schema_data["schema"]["connection"],
                    "tables": tables_with_ref,
                }

                # Extract relationships within this domain
                domain_relationships = []
                for table_name in domain_tables:
                    if table_name in all_tables:
                        for fk in all_tables[table_name].get("foreign_keys", []):
                            domain_relationships.append({
                                "from_table": table_name,
                                "from_columns": fk["columns"],
                                "to_table": fk["referred_table"],
                                "to_columns": fk["referred_columns"],
                                "constraint_name": fk["name"],
                            })

                domain_schema["relationships"] = domain_relationships

                # Save domain file
                domain_file = domains_dir / f"{domain_name}.json"
                with open(domain_file, "w", encoding="utf-8") as f:
                    json.dump(domain_schema, f, indent=2, ensure_ascii=False)

                domain_files.append(str(domain_file))

            # Save domain index
            domain_index = {
                "connection_name": connection_name,
                "total_tables": len(all_tables),
                "total_domains": len(domains),
                "created_at": datetime.now().isoformat(),
                "domains": [
                    {
                        "name": d["name"],
                        "display_name": d.get("display_name", d["name"]),
                        "description": d.get("description", ""),
                        "table_count": len(d["tables"]),
                        "tables": d["tables"],
                        "file_path": f"domains/{d['name']}.json",
                    }
                    for d in domains
                ],
            }

            index_file = base_dir / "domain_index.json"
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(domain_index, f, indent=2, ensure_ascii=False)

            return {
                "saved": True,
                "raw_schema_file": str(raw_file),
                "domain_index_file": str(index_file),
                "domain_files": domain_files,
                "domains_directory": str(domains_dir),
            }

        except Exception as e:
            return {
                "saved": False,
                "error": str(e),
            }
