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
from kode.utils.context import get_current_user_id
from kode.utils.logger import setup_logger
from kode.utils.path_utils import get_safe_connection_path

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
    force_rebuild: bool = Field(
        default=False,
        description="Force rebuild even if ontology exists. Set to True only after user explicitly confirms to rebuild.",
    )
    skip_uncertainty_check: bool = Field(
        default=False,
        description="跳过不确定性问题检查，直接构建本体。"
        "仅在用户明确表示'不回答问卷直接构建'时使用。"
        "注意：跳过检查可能导致本体质量下降。",
    )


class OntologySearchInput(BaseModel):
    """Input schema for OntologySearchTool."""

    ontology_path: str = Field(
        description="Connection name (e.g., 'yanfa') OR path to ontology storage directory (e.g., 'ontology_store/yanfa'). "
        "Recommended: Just pass the connection_name directly. "
        "The tool will automatically find ontology_v2.json."
    )
    query: str = Field(description="Search query (natural language)")
    search_type: str = Field(default="semantic", description="Search type: semantic, exact, fuzzy")
    top_k: int = Field(
        default=10,
        description="基础结果数量（实际返回 top_k*3 个候选后去重）。对于复杂查询，建议设置为 10-15",
    )


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

    Input: connection_name (string), NOT the full schema JSON.

    ⚠️ IMPORTANT - Handle return status:
    - status="success": Done! Summarize statistics to user.
    - status="warning" + gate_check_failed=false: Has unresolved uncertainties.
      → Ask user if they want to skip. If yes, call again with skip_uncertainty_check=true
    - status="warning" + already_exists=true: Ontology exists.
      → Ask user if they want to rebuild. If yes, call again with force_rebuild=true
    - status="error": Failed. Show error message and suggestion to user."""

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
        force_rebuild: bool = False,
        skip_uncertainty_check: bool = False,
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
            force_rebuild: Force rebuild even if ontology exists (requires user confirmation)
            skip_uncertainty_check: 跳过不确定性检查，直接构建（需用户明确确认）

        Returns:
            Ontology as JSON
        """
        try:
            # 🔒 步骤0：检查业务理解是否完成（V2 前置条件）
            from kode.tools.business_understanding import BusinessUnderstandingTool
            from kode.utils.ontology_storage import OntologyStorageV2
            from kode.utils.context import get_current_user_id

            # 🐛 调试日志：检查当前 user_id
            try:
                current_user_id = get_current_user_id()
                logger.info(f"[OntologyBuilder] Current user_id in tool: {current_user_id}")
            except RuntimeError as e:
                logger.error(f"[OntologyBuilder] User context not set: {e}")
                # 不应该发生，但如果发生了，需要明确报错
                return json.dumps(
                    {
                        "status": "error",
                        "gate_check_failed": True,
                        "reason": "user_context_not_set",
                        "message": "❌ 系统错误：用户上下文未设置",
                        "suggestion": "这是一个bug，请联系管理员。工具调用时应该有 user_id 上下文。",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            business_tool = BusinessUnderstandingTool()
            if not business_tool.is_completed(connection_name):
                return json.dumps(
                    {
                        "status": "error",
                        "gate_check_failed": True,
                        "reason": "missing_business_understanding",
                        "message": "❌ 请先运行 BusinessUnderstanding 完成业务理解",
                        "suggestion": "使用 BusinessUnderstanding(connection_name='{}') 开始业务理解".format(
                            connection_name
                        ),
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # Load schema from saved file (with user isolation)
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")
            user_id = get_current_user_id()
            safe_conn_name = get_safe_connection_path(connection_name)
            schema_file = Path(schema_path) / user_id / safe_conn_name / "schema_latest.json"

            if not schema_file.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Schema file not found for connection '{connection_name}'",
                        "expected_path": str(schema_file),
                        "user_id": user_id,
                        "suggestion": "Run DatabaseSchemaExtractor first to extract schema",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # 🔍 检查本体是否已存在（仅当未强制重建时）- 优先 V3，回退 V2
            if not force_rebuild:
                ontology_path = config.get("storage.ontology_path", "./ontology_store")
                # 🔑 修复：添加 user_id 隔离
                conn_path = (
                    Path(ontology_path) / user_id / get_safe_connection_path(connection_name)
                )

                # 使用统一的本体文件名
                existing_ontology_file = conn_path / "ontology.json"

                if existing_ontology_file.exists():
                    # 读取现有本体的元数据
                    try:
                        with open(existing_ontology_file, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)

                        existing_version = existing_data.get("version", "未知")
                        created_at = existing_data.get("meta", {}).get(
                            "created_at", existing_data.get("created_at", "未知")
                        )
                        ontology_stats = existing_data.get("statistics", {})

                        return json.dumps(
                            {
                                "status": "warning",
                                "already_exists": True,
                                "message": f"⚠️ 本体已存在！连接 '{connection_name}' 的本体文件已经存在。",
                                "existing_ontology": {
                                    "file_path": str(existing_ontology_file),
                                    "version": existing_version,
                                    "created_at": created_at,
                                    "statistics": {
                                        "class_count": ontology_stats.get("class_count", 0),
                                        "business_rule_count": ontology_stats.get(
                                            "business_rule_count", 0
                                        ),
                                        "metric_count": ontology_stats.get("metric_count", 0),
                                        "uncertainty_count": ontology_stats.get(
                                            "uncertainty_count", 0
                                        ),
                                    },
                                },
                                "user_message": "是否要重新构建本体？这将覆盖现有的本体文件。如果不需要重新构建，可以直接使用 OntologySearch 工具搜索现有本体。",
                                # ⚠️ Agent 必须读取此字段！
                                "next_action": {
                                    "trigger": "用户说重建/覆盖/重新构建",
                                    "tool": "OntologyBuilder",
                                    "params": {
                                        "connection_name": connection_name,
                                        "force_rebuild": True,
                                    },
                                    "example_call": f"OntologyBuilder(connection_name='{connection_name}', force_rebuild=True)",
                                },
                            },
                            indent=2,
                            ensure_ascii=False,
                        )
                    except Exception as e:
                        logger.warning(f"读取现有本体文件失败: {e}，将继续构建新本体")
                        # 如果读取失败，继续构建流程
            else:
                logger.info(f"🔄 强制重建模式：跳过本体存在性检查，直接构建")

            # ✨ 新架构：不确定性数据已分散存储在各 domain JSON 文件中 (with user isolation)
            domains_dir = (
                Path(schema_path) / user_id / get_safe_connection_path(connection_name) / "domains"
            )
            domain_index_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / "domain_index.json"
            )

            # 🔑 如果没有 domains 目录，自动运行聚类和不确定性分析
            if not domains_dir.exists() or not list(domains_dir.glob("*.json")):
                logger.info(f"📂 未找到 domains 目录，自动运行聚类流程...")

                # 🔄 步骤1：自动运行聚类
                from kode.tools.schema_clustering_tool import DatabaseSchemaClusterer

                clusterer = DatabaseSchemaClusterer()
                # 🔑 确保子工具也能访问用户上下文（虽然当前在主线程，但保持一致性）
                # 注意：这里不需要显式传递，因为还在主线程中，ContextVar 是可用的
                clustering_result_str = clusterer._run(
                    connection_name=connection_name,
                    schema_file=str(schema_file),
                    target_tables_per_domain=10,
                    max_columns_for_analysis=20,
                    llm_model="main",
                    output_language="zh",
                )
                clustering_result = json.loads(clustering_result_str)

                if clustering_result.get("status") != "success":
                    return json.dumps(
                        {
                            "status": "error",
                            "gate_check_failed": True,
                            "reason": "clustering_failed",
                            "message": f"聚类失败: {clustering_result.get('message', '未知错误')}",
                            "suggestion": "请检查 schema 文件是否正确提取。",
                        },
                        indent=2,
                        ensure_ascii=False,
                    )

                logger.info(
                    f"✅ 聚类完成: {clustering_result.get('clustering_summary', {}).get('total_domains', 0)} 个域"
                )

                # 🔄 步骤2：自动运行不确定性分析
                from kode.tools.domain_uncertainty_analyzer import DomainUncertaintyAnalyzer

                analyzer = DomainUncertaintyAnalyzer()
                uncertainty_result_str = analyzer._run(
                    connection_name=connection_name,
                    llm_model="main",
                    max_concurrent_domains=5,
                )
                uncertainty_result = json.loads(uncertainty_result_str)

                if uncertainty_result.get("status") != "success":
                    logger.warning(
                        f"⚠️ 不确定性分析失败: {uncertainty_result.get('message', '未知错误')}"
                    )
                    # 不确定性分析失败不阻塞，继续构建
                else:
                    stats = uncertainty_result.get("statistics", {})
                    logger.info(
                        f"✅ 不确定性分析完成: {stats.get('total_uncertainties', 0)} 个问题 "
                        f"(高: {stats.get('high_priority', 0)}, 中: {stats.get('medium_priority', 0)}, 低: {stats.get('low_priority', 0)})"
                    )

            # 🔍 情况2: 读取所有领域文件，检查 high 优先级不确定性
            high_uncertainties = []
            for domain_file in domains_dir.glob("*.json"):
                try:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        domain_data = json.load(f)

                    # 从领域文件中读取 uncertainties
                    uncertainties = domain_data.get("uncertainties", [])
                    high_uncertainties.extend(
                        [u for u in uncertainties if u.get("priority") == "high"]
                    )
                except Exception as e:
                    logger.warning(f"读取领域文件 {domain_file.name} 失败: {e}")
            unresolved_high = [
                u for u in high_uncertainties if u.get("status") not in ["resolved", "skipped"]
            ]

            if unresolved_high:
                # 生成问题列表（前5个）
                question_list = "\n".join(
                    [
                        f"  {i+1}. [{u.get('domain')}] {u.get('question')}"
                        for i, u in enumerate(unresolved_high[:5])
                    ]
                )

                # 【重构】改为软提示模式：如果用户选择跳过检查，继续构建
                if skip_uncertainty_check:
                    logger.warning(
                        f"⚠️ 用户选择跳过不确定性检查，继续构建本体。"
                        f"未解决的高优先级问题数: {len(unresolved_high)}"
                    )
                else:
                    # 返回软提示，而非硬阻止
                    return json.dumps(
                        {
                            "status": "warning",
                            "gate_check_failed": False,  # 改为 False，表示不是硬性失败
                            "reason": "unresolved_high_priority_uncertainties",
                            "message": f"⚠️ 发现 {len(unresolved_high)} 个未解决的高优先级问题。",
                            "unresolved_count": len(unresolved_high),
                            "total_high_count": len(high_uncertainties),
                            "sample_questions": question_list,
                            # 【关键改动】引导用户去侧边栏填写问卷
                            "user_message": (
                                "建议先回答高优先级问题以提高本体质量。\n"
                                "用户可以：\n"
                                "1. 点击界面右上角的「不确定性」按钮，在侧边栏中填写问卷\n"
                                "2. 或者告诉我「跳过问卷，直接构建本体」（会影响本体质量）"
                            ),
                            # ⚠️ Agent 必须读取此字段！告诉 Agent 如何处理用户选择跳过的情况
                            "next_action": {
                                "trigger": "用户说跳过/不回答/直接构建",
                                "tool": "OntologyBuilder",
                                "params": {
                                    "connection_name": connection_name,
                                    "skip_uncertainty_check": True,
                                },
                                "example_call": f"OntologyBuilder(connection_name='{connection_name}', skip_uncertainty_check=True)",
                            },
                            "sidebar_action": {
                                "type": "open_questionnaire",
                                "connection_name": connection_name,
                                "unresolved_count": len(unresolved_high),
                            },
                        },
                        indent=2,
                        ensure_ascii=False,
                    )

            # ✅ 情况3: 所有 high 问题已解决（或用户选择跳过）
            resolved_count = len(
                [u for u in high_uncertainties if u.get("status") in ["resolved", "skipped"]]
            )
            if skip_uncertainty_check and unresolved_high:
                logger.info(
                    f"⚠️ 用户跳过检查，继续构建。未解决: {len(unresolved_high)}，已解决: {resolved_count}"
                )
            else:
                logger.info(
                    f"✅ 门禁检查通过：所有 {len(high_uncertainties)} 个高优先级问题已解决（resolved: {resolved_count}）"
                )

            # Load schema data
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)

            # Unwrap schema if it has version wrapper
            if "schema" in schema_data and isinstance(schema_data["schema"], dict):
                schema_metadata = schema_data["schema"]
            else:
                schema_metadata = schema_data

            # 🚀 新的简化流程：优先使用 domain_index.json（如果存在）(with user isolation)
            domain_index_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / "domain_index.json"
            )
            database = schema_metadata.get("database", "未知")
            db_schema = schema_metadata.get("schema")

            import asyncio

            # 策略选择：如果有 domain_index.json，使用简化并行流程
            if domain_index_file.exists():
                logger.info(f"✅ 检测到 domain_index.json，使用简化并行构建流程")

                # 🔑 关键修复：在新线程执行前，保存当前上下文
                from kode.utils.context import (
                    get_current_user_id,
                    get_current_conversation_id,
                    set_user_context,
                )

                current_user_id = get_current_user_id()  # 提前获取（在主线程）
                current_conversation_id = get_current_conversation_id()

                # 🔥 关键：在已运行的事件循环中，需要在新线程中运行 asyncio.run
                def run_async_in_thread():
                    """在新线程中运行异步任务（避免嵌套事件循环冲突）"""
                    # 🔑 在新线程中重新设置用户上下文（ContextVar 不跨线程传递）
                    set_user_context(
                        user_id=current_user_id, conversation_id=current_conversation_id
                    )

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
                return json.dumps(
                    {
                        "status": "error",
                        "message": "domain_index.json not found. Please run DomainClusteringTool first to cluster the schema into domains.",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # 🔍 验证本体质量（防止保存空本体或错误本体）
            validation_error = self._validate_ontology(ontology)
            if validation_error:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"❌ 本体构建失败: {validation_error}",
                        "meta": ontology.get("meta", {}),
                        "suggestion": "请检查 schema 是否正确提取，或重新运行构建流程",
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            # Auto-save ontology to file (V2 format)
            if auto_save:
                save_result = self._save_ontology(ontology, connection_name, version)
                ontology["storage"] = save_result

            # Return lightweight summary instead of full ontology (save tokens) - V2 格式
            summary = {
                "status": "success",
                "message": "✅ 本体构建完成（V2格式）",
                "file_path": ontology.get("storage", {}).get("latest_path", ""),
                "statistics": ontology.get(
                    "statistics",
                    {
                        "class_count": len(ontology.get("classes", [])),
                        "business_rule_count": len(ontology.get("business_rules", [])),
                        "metric_count": len(ontology.get("metrics", [])),
                        "data_flow_count": len(ontology.get("data_flows", [])),
                        "uncertainty_count": len(ontology.get("uncertainties", [])),
                    },
                ),
                "domains": ontology.get("domains", []),
                "meta": ontology.get("meta", {}),
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

    def _validate_ontology(self, ontology: Dict[str, Any]) -> Optional[str]:
        """
        验证本体质量，防止保存空本体或错误本体。

        Args:
            ontology: 本体数据

        Returns:
            错误信息（如果验证失败），否则返回 None
        """
        # 检查必需字段
        if not isinstance(ontology, dict):
            return "本体格式错误：不是字典类型"

        # 检查 meta 中是否有错误
        meta = ontology.get("meta", {})
        if "error" in meta:
            return f"构建过程出错: {meta['error']}"

        # 检查是否为空本体（核心字段都为空）
        # 🔑 修复：V3 格式的 classes 在 schema.classes 里，不是顶层
        schema = ontology.get("schema", {})
        classes = schema.get("classes", {})  # V3 格式是字典（domain > tables）
        domains = ontology.get("meta", {}).get("domains", [])

        # V3 格式：classes 是字典，检查是否为空
        if isinstance(classes, dict):
            is_empty = len(classes) == 0
        elif isinstance(classes, list):
            is_empty = len(classes) == 0
        else:
            is_empty = not classes

        if is_empty and not domains:
            return "本体为空：未构建任何业务类或领域"

        # 检查统计信息是否合理
        stats = ontology.get("statistics", {})
        class_count = stats.get("class_count", 0)

        if class_count == 0:
            return "本体无效：class_count 为 0"

        # 一切正常
        return None

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

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """从 AI 输出中提取 JSON（优化版本，快速失败）。"""
        # 策略1：直接解析（最快）
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略2：查找 { } 边界（常见情况）
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                potential_json = text[start_idx : end_idx + 1]
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
        Save ontology to file (V3 format) + 创建版本快照.

        ✨ 自动备份机制：
        - 写入前自动创建时间戳备份
        - 使用临时文件 + 原子替换，防止写入失败损坏数据
        - 自动清理旧备份（保留最近10个）

        Args:
            ontology: Ontology data (V3 format with schema/business_logic/mappings/uncertainties)
            connection_name: Database connection name
            version: Version identifier

        Returns:
            Storage metadata
        """
        import shutil
        import tempfile

        try:
            # Get storage path from config
            config = ConfigManager()
            storage_path = config.get("storage.ontology_path", "./ontology_store")

            # 🔑 修复：添加 user_id 隔离（与 schema_store 保持一致）
            user_id = get_current_user_id()
            base_dir = Path(storage_path)
            conn_dir = base_dir / user_id / get_safe_connection_path(connection_name)
            conn_dir.mkdir(parents=True, exist_ok=True)

            # V3 格式：直接保存 ontology 数据
            # 确保有 version 和 updated_at
            ontology["version"] = ontology.get("version", "3.0")
            ontology["updated_at"] = datetime.now().isoformat()

            # 保存到 ontology.json（带自动备份）
            ontology_file = conn_dir / "ontology.json"

            # ✨ 步骤1：如果主文件存在，先创建备份
            backup_path = None
            if ontology_file.exists():
                backup_dir = conn_dir / "backups"
                backup_dir.mkdir(exist_ok=True)

                # 时间戳格式：ontology.json.backup.20251230_143052_123456（含微秒）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_filename = f"ontology.json.backup.{timestamp}"
                backup_path = backup_dir / backup_filename

                # 复制主文件到备份
                shutil.copy2(ontology_file, backup_path)
                logger.info(f"📦 已备份现有本体到: {backup_path}")

            # ✨ 步骤2：写入临时文件（防止写入失败损坏主文件）
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".json",
                dir=conn_dir,
                text=True
            )
            try:
                with open(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(ontology, f, indent=2, ensure_ascii=False)

                # ✨ 步骤3：验证临时文件完整性
                with open(temp_path, "r", encoding="utf-8") as f:
                    json.load(f)  # 确保可以解析

                # ✨ 步骤4：原子替换（os.replace 在所有平台都是原子操作）
                import os
                os.replace(temp_path, ontology_file)

                logger.info(f"✅ 本体已保存到: {ontology_file}")

            except Exception as e:
                # 清理临时文件
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                raise e

            # ✨ 步骤5：清理旧备份（保留最近10个）
            if backup_path:
                self._cleanup_old_backups(conn_dir / "backups", keep=10)

            # ✅ 版本快照已由 OntologyStorageV2.save_ontology_v2() 自动创建
            # 无需再次调用 OntologyVersionManager（避免重复创建 vN/ 目录）

            return {
                "saved": True,
                "version": ontology["version"],
                "latest_path": str(ontology_file),
                "backup_path": str(backup_path) if backup_path else None,
            }

        except Exception as e:
            logger.error(f"❌ 保存本体失败: {e}")
            return {
                "saved": False,
                "error": str(e),
            }

    def _cleanup_old_backups(self, backup_dir: Path, keep: int = 10) -> None:
        """清理旧备份文件，只保留最近N个

        Args:
            backup_dir: 备份目录
            keep: 保留的备份数量（默认10个）
        """
        if not backup_dir.exists():
            return

        # 获取所有备份文件（按修改时间排序）
        backup_files = sorted(
            backup_dir.glob("ontology.json.backup.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # 最新的在前
        )

        # 删除超出保留数量的旧备份
        for old_backup in backup_files[keep:]:
            try:
                old_backup.unlink()
                logger.info(f"🗑️  已删除旧备份: {old_backup.name}")
            except Exception as e:
                logger.warning(f"删除旧备份失败: {old_backup.name}, 错误: {e}")

    # 🗑️ 已废弃：此方法会重复创建版本目录（与 OntologyStorageV2 冲突）
    # 版本快照已由 OntologyStorageV2.save_ontology_v2() 自动管理
    # 保留方法定义以防其他地方引用，但内部逻辑已移除
    def _create_version_snapshot_async(
        self,
        user_id: str,
        connection_name: str,
        ontology_data: Dict[str, Any],
        change_summary: str
    ) -> Optional[int]:
        """
        [已废弃] 此方法不再使用

        版本快照由 OntologyStorageV2 统一管理，无需额外调用
        """
        logger.debug("⚠️ _create_version_snapshot_async 已废弃，跳过执行")
        return None

    def _build_qa_text(self, business_context: Dict[str, Any]) -> str:
        """从业务上下文构建问答文本

        优先级：qa_pairs > answers
        """
        # 1. 优先使用 qa_pairs（包含完整问题文本）
        qa_pairs = business_context.get("qa_pairs", [])
        if qa_pairs:
            lines = []
            for i, pair in enumerate(qa_pairs, 1):
                question = pair.get("question", "")
                answer = pair.get("answer", "（未回答）")
                if question:
                    lines.append(f"**Q{i}: {question}**")
                    lines.append(f"A: {answer}")
                    lines.append("")
            return "\n".join(lines).strip()

        # 2. 回退到 answers（只有答案，问题文本丢失）
        answers = business_context.get("answers", {})
        if answers:
            lines = []
            for i, (key, answer) in enumerate(answers.items(), 1):
                # 从 key 推断问题类型
                label = key.replace("q", "Q").replace("_", " ").title()
                lines.append(f"**{label}**")
                lines.append(f"A: {answer}")
                lines.append("")
            return "\n".join(lines).strip()

        return ""

    def _prepare_domain_schema(
        self, domain_schema: Dict[str, Any], max_sample_rows: int = 3
    ) -> str:
        """
        为域准备详细schema文本（含样例数据智能摘要）。

        Args:
            domain_schema: 域的 schema 数据
            max_sample_rows: 每个表最多包含的样例数据行数（默认 3 行，避免 prompt 过长）
        """
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

            # 🔧 限制样例数据行数，避免 prompt 过长导致超时
            sample_data = table_data.get("sample_data", {})
            if sample_data and sample_data.get("rows"):
                rows = sample_data["rows"]
                row_count = sample_data.get("row_count", len(rows))

                # 只取前 N 行
                rows_to_show = rows[:max_sample_rows]

                lines.append(f"  样例数据(共{row_count}条，显示前{len(rows_to_show)}条):")
                for row in rows_to_show:
                    lines.append(f"    {json.dumps(row, ensure_ascii=False)}")

            lines.append("")
        return "\n".join(lines)

    def _load_business_questions(self, connection_name: str, business_tool) -> Dict[str, str]:
        """
        加载业务问题列表（key -> 问题文本）

        优先从 business_context.json 读取（完成后保存的），
        其次从 InteractiveTool 的状态文件读取（问卷进行中）。

        Args:
            connection_name: 数据库连接名
            business_tool: BusinessUnderstandingTool 实例

        Returns:
            {问题key: 问题文本} 的映射
        """
        questions_map = {}

        # 1. 优先从 business_context.json 读取（问卷完成后的完整数据）
        context = business_tool.storage.load_business_context(connection_name)
        if context and "questions" in context:
            # questions 格式: {key: question_text}
            questions_map = context["questions"]
            return questions_map

        # 2. 其次从 interaction_state 缓存读取（问卷进行中）
        state = business_tool._load_state(connection_name)
        if state and "questions" in state:
            # questions 格式: [(key, question_text, hint), ...]
            for item in state["questions"]:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    key, question_text = item[0], item[1]
                    questions_map[key] = question_text

        return questions_map

    def _merge_ontologies(
        self,
        domain_ontologies: Dict[str, Dict[str, Any]],
        cross_domain_insights: Dict[str, Any],
        global_context: Dict[str, Any],
        schema_metadata: Dict[str, Any],
        connection_name: str,
        model_manager,
    ) -> Dict[str, Any]:
        """合并所有域的本体+跨域洞察。"""
        (
            all_concepts,
            all_properties,
            all_relationships,
            all_hierarchies,
            all_uncertainties,
            all_axioms,
        ) = ({}, {}, [], [], [], [])

        for ont in domain_ontologies.values():
            all_concepts.update(ont.get("concepts", {}))
            all_properties.update(ont.get("properties", {}))
            all_relationships.extend(ont.get("relationships", []))
            all_hierarchies.extend(ont.get("hierarchies", []))
            all_uncertainties.extend(ont.get("uncertainties", []))
            all_axioms.extend(ont.get("axioms", []))

        all_relationships.extend(cross_domain_insights.get("relationships", []))
        all_hierarchies.extend(cross_domain_insights.get("global_hierarchies", []))

        domain_insights = cross_domain_insights.get("global_insights", {})
        if not domain_insights:
            domain_insights = {
                "primary_domain": global_context.get("architecture_pattern", "未知"),
                "sub_domains": list(domain_ontologies.keys()),
                "business_scenario": global_context.get("insights", ""),
                "architecture_pattern": global_context.get("architecture_pattern", "未知"),
            }

        # 跨域公理（如跨表的派生规则）
        all_axioms.extend(cross_domain_insights.get("axioms", []))

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
                "phase3_cross_relations": len(cross_domain_insights.get("relationships", [])),
            },
            "concepts": all_concepts,
            "properties": all_properties,
            "relationships": all_relationships,
            "hierarchies": all_hierarchies,
            "domain_insights": domain_insights,
            "axioms": all_axioms,
            "uncertainties": all_uncertainties,
            "recommendations": [],
            "statistics": {
                "concept_count": len(all_concepts),
                "property_count": len(all_properties),
                "relationship_count": len(all_relationships),
                "hierarchy_count": len(all_hierarchies),
                "axiom_count": len(all_axioms),
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

            # 1. 读取 domain_index.json (with user isolation)
            user_id = get_current_user_id()
            domain_index_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / "domain_index.json"
            )
            with open(domain_index_file, "r", encoding="utf-8") as f:
                domain_index = json.load(f)

            domains = domain_index["domains"]
            logger.info(f"📋 加载到 {len(domains)} 个业务域")

            # 2. 初始化模型（添加超时和重试配置）
            config_manager = ConfigManager()
            config = config_manager.get_all()

            # 🔧 修改配置：增加超时时间和重试次数
            if "models" not in config:
                config["models"] = {}

            # 确保 main 模型有正确的配置
            main_model_name = config.get("modelPointers", {}).get("main", "claude-sonnet-4-5")
            if main_model_name not in config["models"]:
                config["models"][main_model_name] = {
                    "provider": "anthropic",
                    "model_id": main_model_name,
                }

            # 注入超时和重试配置到 extra_params
            if isinstance(config["models"][main_model_name], dict):
                if "extra_params" not in config["models"][main_model_name]:
                    config["models"][main_model_name]["extra_params"] = {}
                config["models"][main_model_name]["extra_params"].update(
                    {
                        "timeout": 1200.0,  # 增加到 120 秒
                        "max_retries": 5,  # 增加重试次数到 5 次
                    }
                )

            model_manager = ModelManager(config)
            model = model_manager.get_model("main")
            model.temperature = 0.0
            model.max_tokens = 64000

            logger.info(f"✅ 模型配置完成：timeout=120s, max_retries=5, max_tokens=64000")

            # 3. 并行构建所有域
            t_start = time.time()
            domain_ontologies = await self._build_all_domains_parallel(
                domains=domains,
                connection_name=connection_name,
                schema_path=schema_path,
                database=database,
                db_schema=db_schema,
                model=model,
            )
            t_elapsed = time.time() - t_start
            logger.info(f"✅ 并行构建完成：{len(domain_ontologies)} 个域，耗时 {t_elapsed:.2f}s")

            # 4. 轻量级合并（无需AI）
            final_ontology = self._merge_domain_ontologies_simple(
                domain_ontologies=domain_ontologies,
                connection_name=connection_name,
                database=database,
                model_manager=model_manager,
            )

            logger.info(f"🎉 本体构建完成：{final_ontology['statistics']['class_count']} 个类")
            return final_ontology

        except Exception as e:
            logger.error(f"简化构建失败: {str(e)}", exc_info=True)
            return {
                "version": "2.0",
                "meta": {
                    "created_at": datetime.now().isoformat(),
                    "created_by": "error_simplified",
                    "error": str(e),
                },
                "domains": [],
                "classes": [],
                "business_rules": [],
                "metrics": [],
                "data_flows": [],
                "uncertainties": [],
                "statistics": {
                    "class_count": 0,
                    "business_rule_count": 0,
                    "metric_count": 0,
                    "data_flow_count": 0,
                    "uncertainty_count": 0,
                    "domain_count": 0,
                },
            }

    async def _build_all_domains_parallel(
        self,
        domains: List[Dict[str, Any]],
        connection_name: str,
        schema_path: str,
        database: str,
        db_schema: Optional[str],
        model,
    ) -> Dict[str, Dict[str, Any]]:
        """
        并行构建所有业务域的本体（核心性能优化）。

        使用 asyncio.gather() + Semaphore(10) 限流，避免 API 限速。
        """
        import asyncio
        import time

        # 📡 发送总体开始消息
        total_tables = sum(d.get("table_count", 0) for d in domains)
        start_msg = f"📋 开始并行构建本体：共 {len(domains)} 个业务域，{total_tables} 个表"
        logger.info(start_msg)
        await self.send_progress(
            content=start_msg,
            stage="ontology_build_start",
            total_domains=len(domains),
            total_tables=total_tables,
        )

        async def build_single_domain(domain_info: Dict[str, Any], domain_index: int) -> tuple:
            """异步构建单个域。"""
            domain_name = domain_info["name"]
            t_start = time.time()

            # 📡 发送进度消息到前端
            progress_msg = f"🚀 开始构建 {domain_name}（{domain_info['table_count']} 个表）"
            logger.info(progress_msg)
            await self.send_progress(
                content=progress_msg,
                stage="ontology_build",
                domain=domain_name,
                current=domain_index + 1,
                total=len(domains),
                table_count=domain_info["table_count"],
            )

            # 读取领域的完整 schema (with user isolation)
            user_id = get_current_user_id()
            domain_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / domain_info["file_path"]
            )
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
                model=model,
            )
            t_ai_elapsed = time.time() - t_ai_start

            t_elapsed = time.time() - t_start

            # 📡 发送完成消息到前端
            complete_msg = f"✅ {domain_name} 完成（{domain_info['table_count']} 个表，AI耗时 {t_ai_elapsed:.2f}s，总耗时 {t_elapsed:.2f}s）"
            logger.info(complete_msg)
            await self.send_progress(
                content=complete_msg,
                stage="ontology_build_complete",
                domain=domain_name,
                current=domain_index + 1,
                total=len(domains),
                ai_time=round(t_ai_elapsed, 2),
                total_time=round(t_elapsed, 2),
            )

            return domain_name, domain_ont

        # 限流并发（最多10个同时）
        from asyncio import Semaphore

        semaphore = Semaphore(10)

        async def bounded_task(domain_info_with_index):
            domain_info, domain_index = domain_info_with_index
            async with semaphore:
                # 添加重试机制（最多重试 3 次）
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        return await build_single_domain(domain_info, domain_index)
                    except Exception as e:
                        # 提取异常详情
                        error_type = type(e).__name__
                        error_msg = str(e)

                        if attempt == max_retries - 1:
                            # 最后一次重试失败，抛出异常
                            logger.error(
                                f"❌ 域 {domain_info['name']} 构建失败（重试 {max_retries} 次后）\n"
                                f"   错误类型: {error_type}\n"
                                f"   错误信息: {error_msg}\n"
                                f"   表数量: {domain_info.get('table_count', 0)}"
                            )
                            raise
                        else:
                            # 重试前等待（指数退避）
                            wait_time = 2**attempt
                            logger.warning(
                                f"⚠️ 域 {domain_info['name']} 构建失败（第 {attempt + 1}/{max_retries} 次尝试），{wait_time}s 后重试\n"
                                f"   错误类型: {error_type}\n"
                                f"   错误信息: {error_msg}"
                            )
                            await asyncio.sleep(wait_time)

        # 并行执行（传递索引以便计算进度）
        # 使用 return_exceptions=True 确保单个域失败不影响整体
        overall_start = time.time()
        results = await asyncio.gather(
            *[bounded_task((d, i)) for i, d in enumerate(domains)], return_exceptions=True
        )
        overall_elapsed = time.time() - overall_start

        # 分离成功和失败的结果
        successful_results = []
        failed_domains = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                domain_name = domains[i]["name"]
                failed_domains.append(domain_name)
                logger.error(f"❌ 域 {domain_name} 构建失败: {str(result)}")
            else:
                successful_results.append(result)

        # 📡 发送总体完成消息
        success_count = len(successful_results)
        fail_count = len(failed_domains)
        finish_msg = f"🎉 本体构建完成！成功 {success_count}/{len(domains)} 个域"
        if fail_count > 0:
            finish_msg += f"，失败 {fail_count} 个域: {', '.join(failed_domains)}"
        finish_msg += f"，总耗时 {overall_elapsed:.2f}s"

        logger.info(finish_msg)
        await self.send_progress(
            content=finish_msg,
            stage="ontology_build_finish",
            total_domains=len(domains),
            success_domains=success_count,
            failed_domains=fail_count,
            total_time=round(overall_elapsed, 2),
        )

        # 转换为字典（只包含成功的结果）
        return {domain_name: ontology for domain_name, ontology in successful_results}

    async def _ai_build_domain_ontology(
        self,
        domain_name: str,
        domain_schema: Dict[str, Any],
        connection_name: str,
        database: str,
        db_schema: Optional[str],
        model,
    ) -> Dict[str, Any]:
        """
        为单个业务域构建本体（V3 格式，异步并行化版本）。

        直接生成 V3 格式：classes/business_rules/metrics/data_flows
        """
        from langchain_core.messages import HumanMessage

        # 准备领域 schema 文本
        domain_schema_text = self._prepare_domain_schema(domain_schema)

        # 🔥 加载业务理解问答
        from kode.tools.business_understanding import BusinessUnderstandingTool

        business_tool = BusinessUnderstandingTool()
        business_context = business_tool.storage.load_business_context(connection_name) or {}

        # 🔑 从 qa_pairs（优先）或 answers（回退）构建问答文本
        qa_text = self._build_qa_text(business_context)

        # 构建业务描述（Input 1: 应然层）
        business_context_section = ""
        if qa_text:
            business_context_section = f"""
# Input 1: 业务描述（应然层）

{qa_text}

---

**重要说明**：
- 根据以上业务描述判断概念的 `importance`（critical/important/optional）
- 判断标准：核心业务概念为 critical，支撑性概念为 important，辅助性概念为 optional
"""

        # 🔥 加载并注入不确定性的答案
        uncertainty_rules = self._load_high_priority_rules(connection_name, domain_name)
        uncertainty_section = ""
        if uncertainty_rules:
            uncertainty_section = "\n\n# 🔒 用户已确认的业务规则（必须遵守）\n\n"
            uncertainty_section += uncertainty_rules
            uncertainty_section += "\n**重要**: 构建本体时必须严格遵循上述规则！\n"

        # 🔥 完全使用产品经理的提示词（V3 格式 + 新版改进）
        prompt = f"""你是一名专业的语义层数据建模师（Semantic-Layer Modeling Agent）。

任务是：根据用户回答的业务问题 + 用户的数据库的 schema，构建一个语义清晰、可审计、可映射的数据本体（Ontology），并基于用户需求引导本体执行各种分析类需求，交付结果。

---

# 当前上下文

**业务域**: {domain_name}
**数据库**: {database}
**Schema**: {db_schema or "默认"}

{business_context_section}
{uncertainty_section}

---

# Input 1: 业务描述（应然层）

{business_context_section if business_context_section else "**无业务上下文**：用户未提供业务描述，仅基于数据库结构推断。"}

用户会描述他们的场景，可能包括：
- 这是什么：一句话描述（如"个人知识库"、"电商平台"、"SaaS订阅服务"）
- 核心目标：想达成什么（如"帮助用户整理知识"、"提升转化率"）
- 主要对象：业务中的核心概念（如"文章、标签、用户"）
- 关键动作：主要操作流程（如"发布文章、添加评论、搜索"）
- 业务规则：特殊约束（如"试用期只能用基础功能"）
- 目标指标：关键指标（如"月活、转化率、GMV"）

**注意**：业务描述通常是不完整的，需要你通过提问补充。

---

# Input 2: 数据库结构（实然层）

{domain_schema_text}

**注意**：数据库结构是客观的，但可能包含冗余或不规范的设计。

---

# 核心处理逻辑：应然与实然的对齐

## 第一步：双向提取

### 从业务描述提取（应然）：

**应然推理原则（奥卡姆剃刀）**：只提取业务描述中明确需要的概念，不做泛化推理。

**允许提取**：
- 业务描述中直接提到的实体、动作、规则
- 业务目标逻辑上必需的概念（如"订阅收入"必然需要"订阅"和"收入"）
- 商业模式内在的必要概念（如 SaaS 必然有订阅/续费/流失）

**禁止推理**：
- ❌ "用户系统一般有性别/城市/生日" → 和业务没有直接关系就不是应然

**判断标准**：
这个概念是否在业务描述中被直接或间接提及？
- 直接提及 → 应然有
- 业务目标逻辑必需 → 应然有
- 仅基于"一般XX系统都有"的推测 → 不是应然

**提取内容**：
- **核心实体**: 从业务描述的名词提取，如"用户"、"订单"、"课程"
- **关键动作**: 从业务描述的动词提取，如"购买"、"发布"、"评论"
- **业务规则**: 从业务描述的约束提取，如"满100包邮"、"VIP专属"
- **目标指标**: 从业务描述的KPI提取，如"转化率"、"留存率"

### 从数据库结构提取（实然）：

数据模型 = {{
    候选实体: [每个表作为候选，按业务含义决定是否建类、是否合并、是否拆分],
    属性: [表的列 → 类的属性],
    关系: [外键 → belongs_to/has_many, 关联表 → many_to_many],
    约束: [NOT NULL, UNIQUE, CHECK → 业务规则],
    生命周期: [状态字段 → lifecycle_states]
}}

## 第二步：四象限对齐矩阵

将提取的内容按以下逻辑分类：

### 象限1：应然有 ∩ 实然有（完美对齐）✅
**处理**: 直接建模，整合两边信息

**示例**:
- 业务描述："用户可以发布文章"
- 数据库：有 users 表和 posts 表，posts.author_id 关联 users.id
- **输出**:
  - schema.classes.User (完整属性)
  - schema.classes.Post (完整属性)
  - schema.relationships.Author_Post (1:N关系)

---

### 象限2：应然有 ∩ 实然无（需求缺失）⚠️

**注意**：只有通过"应然推理原则"判定为应然的概念，才进入此象限。

**处理**:
1. 如果是核心概念 → 记录到 uncertainties (severity: high, type: missing_in_database)
2. 如果是次要概念 → 记录到 uncertainties (severity: medium/low, type: missing_in_database)

**示例**:
- 业务描述："用户可以关注其他用户"
- 数据库：没有 follows 表
- **判断**:
  - IF 这是核心功能 THEN
    uncertainties.push({{
      id: "UC_XXX",
      entity: "[missing] follows",
      type: "missing_in_database",
      severity: "high",
      data_source: "business",
      issues: [{{
        question: "用户关注功能需要 follows 表，但数据库中不存在"
      }}],
      suggested_action: "创建 follows 表 (follower_id, followee_id)"
    }})

---

### 象限3：应然无 ∩ 实然有（数据库有但业务没提）🤔
**处理**: 分情况
1. 可能是用户遗漏 → 推断业务含义和相关性，加入模型，标注 data_source: "inferred"
2. 技术实现细节 → 记录但标注为 technical
3. 冗余/废弃字段 → 标注 deprecated: true

**示例**:
- 数据库：posts 表有 view_count 字段
- 业务描述：没提到浏览统计
- **推断**:
  - 这可能是重要的分析指标，用户可能忘了提
- **输出**:
  - 加入 schema.classes.Post.view_count
  - 在 uncertainties 中添加：
    {{
      entity: "posts.view_count",
      type: "missing_context",
      severity: "low",
      data_source: "inferred",
      issues: [{{
        question: "业务描述中未提及浏览统计，已从数据库推断加入，请确认是否需要相关的统计功能"
      }}]
    }}

---

### 象限4：应然无 ∩ 实然无（都没有）
**处理**: 不处理（不存在的东西不建模）

## 第三步：冲突检测与决策

### 1. 定义冲突（Definition Conflicts）

**场景A：命名不一致**
- 业务："文章状态有草稿、已发布"
- 数据库：posts.status ENUM('draft', 'published', 'archived', 'deleted')
- **冲突**: 业务只提了2种状态，数据库有4种
- **处理**: 记录到 uncertainties (type: definition_conflict)

**场景B：类型不一致**
- 业务："价格精确到分"
- 数据库：products.price INTEGER（存储的是"分"的整数值）
- **处理**: 不冲突，但需要在 constraint 中说明："数据库存储整数，如1999=19.99元，应用层需要转换"

### 2. 关系基数冲突

**示例**:
- 业务："一个订单属于一个用户"
- 数据库：orders.user_id 有 UNIQUE 约束
- **冲突**: UNIQUE约束意味着 1个用户只能有1个订单（1:1），但业务语义应该是1:N
- **处理**: 记录到 uncertainties (type: definition_conflict, severity: high)

### 3. 缺少外键

**示例**:
- 业务："评论属于文章"
- 数据库：comments 表有 post_id 字段，但没有 FOREIGN KEY 约束
- **处理**: 记录到 uncertainties (type: missing_constraint, severity: low)，但仍假设为外键关系

### 4. 业务规则与数据约束不一致

**示例**:
- 业务："文章标题不能为空"
- 数据库：posts.title VARCHAR(200) NULL
- **冲突**: 业务规则要求title非空，但数据库允许NULL
- **处理**: 记录到 uncertainties (type: definition_conflict, severity: medium)

---

# 格式规范 (Format Standards)

本节定义本体构建过程中必须遵守的格式规范，确保输出一致性和可解析性。

## Entity 定位规范 (Entity Location Rules)

在本体任何位置描述实体、字段、关系时，必须使用完整定位路径，禁止使用模糊表述。

**基础规则**:

| 问题类型 | 正确格式 | 错误格式 |
|---------|---------|---------|
| 单表单字段 | `table_name.field_name` | `field_name` |
| 单表多字段 | `table_name.(field_a, field_b)` | `table_name.field_a vs field_b` |
| 多表同名字段 | `(table_a, table_b).field_name` | `多表.field_name` |
| 多表多字段 | `(table_a, table_b).(field_x, field_y)` | `多表.field_x/field_y` |
| 表关系 | `table_a ↔ table_b` | `table_a 和 table_b` |
| 跨表字段映射 | `table_a.field_a ↔ table_b.field_b` | `table_a.field_a → table_b` |
| 本体内路径 | `schema.classes.ClassName.attributes.field` | `ClassName.field` |

**禁止使用**:
- vs、/、和、或 等自然语言连接词
- 裸字段名（不带表名前缀）
- 裸表名（不带问题类型标注，当描述表级问题时）
- 中文表名描述（如"多表"、"多个表"）

**表级问题标注**:

当问题针对整张表或跨表模式时，使用方括号标注问题类型：

| 场景 | 格式 | 示例 |
|-----|-----|-----|
| 缺失的表 | `[missing] table_name` | `[missing] api_call` |
| 表名拼写问题 | `[typo] table_name` | `[typo] platform_ai_agent_categray` |
| 孤立表（无关联） | `[orphan] table_name` | `[orphan] backup_logs` |
| 跨表模式问题 | `[pattern] *.field_name` | `[pattern] *.(created_by, updated_by)` |
| 废弃表 | `[deprecated] table_name` | `[deprecated] old_user_logs` |

**示例值规范**:

1. **example 必须基于数据库中的真实数据，禁止编造**
2. 如果字段实际数据全为 NULL 或无有效值，不填写 example，改为标注：
   `"actual_data": "全为NULL"` 或 `"actual_data": "无有效数据"`
3. **禁止使用占位符**（如 "【填写ID】"、"TODO"、"张三"）
4. **禁止基于字段名推测示例值**（如看到 sex 就填 "1"，看到 nick_name 就填 "张三"）

---

# 输出结构

## 1. meta（元信息）

**数据来源**：从 业务描述（应然层）块中 提取业务信息填充。

**字段映射**：

| meta 字段 | 来源 |
|----------|------|
| ontology_name | `{{domain_name}}_Ontology` |
| version | 默认 "1.0.0"，后续迭代递增 |
| domain_type | 从 业务描述（应然层）块中提取 |
| scenario_description | 从 业务描述（应然层）块中提取一句话概述 |
| core_goal | 从 业务描述（应然层）块中提取 "核心目标"或"想达成什么"提取 |
| key_activities | 从 业务描述（应然层）块中提取 "关键动作"或"主要操作流程"提取 |
| design_note | 本体设计说明（可选） |

**必须填充**：所有字段不得为空。如果 business_context.json 中缺少相关信息，在 uncertainties 中记录，并基于数据库结构推断一个初始值。

```json
{{{{
  "meta": {{{{
    "ontology_name": "{domain_name}_Ontology",
    "version": "1.0.0",
    "domain_type": "根据业务上下文判断（如 SaaS-Subscription、E-Commerce、Content-Platform）",
    "scenario_description": "从 business_context.json 提取的一句话业务场景描述",
    "core_goal": "从 business_context.json 提取的核心目标",
    "key_activities": ["从 business_context.json 提取的关键动作"],
    "design_note": "本体设计说明（可选）"
  }}}}
}}}}
```

## 2. schema（概念定义）

### 2.1 classes（业务类）

业务类是对业务概念的抽象，不必与数据库表一一对应。

**类与表的关系**：
- 一个类可以映射到多个表（如 User 整合 users + user_profiles）
- 一个表可以拆分为多个类（如按业务边界拆分）
- 类可以没有对应的表（业务概念，待实现）
- 表可以不建类（技术细节，非业务概念）

类与表的具体映射关系在 `mappings.objects` 中定义。

按业务域分组，使用**对象格式**：

```json
{{{{
  "classes": {{{{
    "{domain_name}": {{{{
      "orders": {{{{
        "class_type": "concrete_class",
        "description": "业务描述（100字以内）",
        "why": "为什么这个类重要",
        "importance": "critical/high/medium/low",
        "lifecycle_states": ["状态1", "状态2"],
        "attributes": {{{{
          "id": {{{{
            "type": "bigint",
            "example": "10001",
            "constraint": "主键，自增"
          }}}},
          "status": {{{{
            "type": "varchar(20)",
            "example": "pending",
            "constraint": "非空，枚举值",
            "why": "状态驱动订单流转"
          }}}}
        }}}},
        "relations": {{{{
          "belongs_to": "users",
          "has_many": ["order_items"],
          "many_to_many": {{{{
            "products": {{{{
              "through": "order_items",
              "why": "订单包含多个商品"
            }}}}
          }}}}
        }}}}
      }}}}
    }}}}
  }}}}
}}}}
```

**重要**: `classes` 的第一层 key 是当前域名（`{domain_name}`），第二层 key 才是表名。

### 2.2 properties（共享属性定义）

当多个类（表）共享相同的字段模式时，必须将其抽取到 `schema.properties` 中统一定义，避免重复描述。

**识别条件**（满足任意2条即触发）：
- 字段名相同或相似（如 created_by / create_by / creator_id）
- 字段在 ≥3 个表中出现
- 业务含义相同

**处理流程**：
```
IF 字段在 >=3 个表中出现 AND 业务含义相同
THEN
  1. 在 schema.properties 中定义该属性
  2. 记录 used_by 列表（哪些类使用）
  3. 如有命名变体，记录 naming_variants
  4. 各 class 引用该 property（不重复定义属性细节）
```

**schema.properties 结构**（注意：properties 在 schema 内部，与 classes 同级）：

```json
{{{{
  "schema": {{{{
    "properties": {{{{
      "audit_fields": {{{{
      "description": "审计字段组 - 记录数据创建和修改信息",
      "fields": {{{{
        "created_by": {{{{
          "type": "string",
          "description": "创建者ID",
          "foreign_key": "User.id"
        }}}},
        "created_at": {{{{
          "type": "datetime",
          "description": "创建时间"
        }}}},
        "updated_by": {{{{
          "type": "string",
          "description": "最后修改者ID"
        }}}},
        "updated_at": {{{{
          "type": "datetime",
          "description": "最后修改时间"
        }}}}
      }}}},
      "used_by": ["orders", "users", "products", "comments"],
      "naming_variants": {{{{
        "created_by": ["create_by", "creator_id"],
        "updated_at": ["update_at", "last_modify_at", "modify_time"]
      }}}},
      "consistency_note": "存在命名变体，建议统一为 created_by/updated_by 格式"
    }}}},
    "soft_delete": {{{{
      "description": "软删除标记",
      "fields": {{{{
        "deleted_at": {{{{
          "type": "datetime",
          "nullable": true,
          "description": "删除时间，NULL表示未删除"
        }}}}
      }}}},
      "used_by": ["orders", "users", "products"],
      "why": "支持数据恢复和审计追溯"
    }}}}
    }}}}
  }}}}
}}}}
```

**常见通用属性组**：
- `audit_fields`: created_by, created_at, updated_by, updated_at
- `soft_delete`: deleted_at, is_deleted
- `status_enum`: status（各表具体枚举值不同，但模式相同）
- `tenant_isolation`: tenant_id, org_id

### 2.3 relationships（关系定义）

多对多关系需要单独定义：

```json
{{{{
  "relationships": {{{{
    "Post_Tag": {{{{
      "type": "many_to_many",
      "from": "Post",
      "to": "Tag",
      "through": "PostTag",
      "junction_table": {{{{
        "table_name": "post_tags",
        "fields": {{{{
          "post_id": "foreign_key → Post.id",
          "tag_id": "foreign_key → Tag.id"
        }}}},
        "unique_constraint": ["post_id", "tag_id"]
      }}}},
      "why": "关系存在的业务原因"
    }}}}
  }}}}
}}}}
```

## 3. business_logic（业务逻辑）

### 3.1 rules（业务规则）

```json
{{{{
  "rules": {{{{
    "Rule_Name": {{{{
      "name": "规则名称",
      "type": "validation_rule/invariant/constraint/derivation",
      "applies_to": ["Class1", "Class2"],
      "conditions": ["条件1", "条件2"],
      "action": "IF 条件满足 THEN 动作 ELSE 替代动作",
      "why": "为什么需要这个规则",
      "confidence": "high/medium/low",
      "source": "constraint/comment/naming/pattern"
    }}}}
  }}}}
}}}}
```

### 3.2 flows（业务流程）

```json
{{{{
  "flows": {{{{
    "flow_name": {{{{
      "description": "流程描述",
      "steps": [
        {{{{
          "step": 1,
          "actor": "User/System",
          "action": "动作描述",
          "validation": "Rule_Name（如果有）",
          "on_fail": "失败处理（如果有）"
        }}}}
      ]
    }}}}
  }}}}
}}}}
```

## 4. mappings（数据源映射）

**映射场景说明**：

| 场景 | tables | primary_table | join_logic |
|------|--------|---------------|------------|
| **场景1：单表映射（1类 → 1表）** | `["posts"]` | `"posts"` | 不需要 |
| **场景2：多表合并（1类 → N表）** | `["users", "user_profiles"]` | `"users"` | `"users.id = user_profiles.user_id"` |
| **场景3：表拆分（N类 → 1表）** | 每个类的 mappings 指向同一个表的不同字段子集 | - | - |
| **场景4：无表映射** | 不填写 mappings，在 uncertainties 中记录 | - | - |

```json
{{{{
  "mappings": {{{{
    "objects": {{{{
      "ClassName": {{{{
        "source": {{{{
          "type": "postgresql/mysql/sqlserver",
          "tables": ["table_name"],
          "primary_table": "table_name",
          "primary_key": "id",
          "join_logic": "多表时的关联逻辑（可选）"
        }}}},
        "field_mapping": {{{{
          "business_field": "table_name.db_column"
        }}}},
        "indexes": {{{{
          "primary": "id",
          "unique": ["unique_field"],
          "regular": ["indexed_field"]
        }}}}
      }}}}
    }}}},
    "metrics": {{{{
      "metric_name": {{{{
        "description": "指标描述",
        "definition": "业务定义",
        "calculation": {{{{
          "formula": "计算公式或SQL"
        }}}},
        "refresh_frequency": "刷新频率（可选）"
      }}}}
    }}}}
  }}}}
}}}}
```

## 5. uncertainties（不确定性清单）

**重要**: 将所有发现的问题、缺失、冲突统一记录到此处。

### type 类型定义：

| type | 含义 | 典型场景 |
|------|------|---------|
| `missing_in_database` | 业务需要但数据库缺失 | 象限2：业务提到的表/字段不存在 |
| `missing_context` | 数据库有但业务未说明 | 象限3：推断加入，需确认用途 |
| `definition_conflict` | 业务与数据库定义冲突 | 枚举值不一致、约束不匹配 |
| `schema_ambiguity` | 数据库结构不明确 | 缺少外键、字段含义模糊 |
| `field_ambiguity` | 字段业务含义不明 | 多个相似字段，用途不清 |
| `naming_inconsistency` | 跨表命名不统一 | 同一概念不同表用不同字段名 |
| `table_not_found` | 表缺失 | 业务流程需要但表不存在 |
| `multiple_issues` | 单实体多问题聚合 | 一个表有多个不同类型问题 |

### 聚合规则（必须遵守）

**禁止**: 同一 entity 在 uncertainties 中重复出现。当多个表存在同样的问题时，聚合为模式级问题。

| 情况 | 处理方式 |
|-----|---------|
| 同一表的多个问题 | 合并为一条，用 `issues` 数组列出 |
| 多表的同类问题 | 提取为 `[pattern]` 级问题，记录 `affected_tables` |
| 同一字段的多角度问题 | 合并为一条，在 `issues` 中分项描述 |

### 严重性判断

- `high`: 核心逻辑冲突，必须立即解决（如关系基数错误）
- `medium`: 需要明确但可以暂时假设（如字段含义不明）
- `low`: 轻微不一致，不影响主流程（如命名风格）

```json
{{{{
  "uncertainties": [
    {{{{
      "id": "UC_001",
      "entity": "表名 或 [标注] 表名",
      "type": "missing_in_database/missing_context/definition_conflict/schema_ambiguity/field_ambiguity/naming_inconsistency/table_not_found/multiple_issues",
      "severity": "high/medium/low",
      "data_source": "business/database/inferred",
      "issues": [
        {{{{
          "type": "问题子类型（可选）",
          "field": "相关字段（可选）",
          "question": "具体的疑问描述",
          "context": "产生疑问的上下文（可选）"
        }}}}
      ],
      "affected_tables": ["table_a", "table_b"],
      "options": [
        {{{{"option": "A", "solution": "方案描述"}}}}
      ],
      "suggested_action": "建议的解决方案"
    }}}}
  ]
}}}}
```

---

# ***本体完整最终输出示例***

```json
{{{{
  "meta": {{{{
    "ontology_name": "{domain_name}_Ontology",
    "version": "1.0.0",
    "domain_type": "交易管理",
    "scenario_description": "电商平台订单交易管理域",
    "core_goal": "管理用户订单的完整生命周期",
    "key_activities": ["下单", "支付", "发货", "完成"]
  }}}},

  "schema": {{{{
    "classes": {{{{
      "{domain_name}": {{{{
        "orders": {{{{
          "class_type": "concrete_class",
          "description": "订单实体，记录用户的购买交易",
          "why": "订单是交易的核心载体，连接用户、商品、支付、物流",
          "importance": "critical",
          "lifecycle_states": ["pending", "paid", "shipped", "completed", "cancelled"],
          "attributes": {{{{
            "id": {{{{
              "type": "bigint",
              "example": "10001",
              "constraint": "主键，自增"
            }}}},
            "status": {{{{
              "type": "varchar(20)",
              "example": "paid",
              "constraint": "非空，枚举值",
              "why": "状态驱动订单流转和权限控制"
            }}}},
            "total_amount": {{{{
              "type": "decimal(10,2)",
              "example": "299.00",
              "constraint": ">= 0",
              "why": "核心财务字段，影响收入统计"
            }}}},
            "user_id": {{{{
              "type": "bigint",
              "example": "1001",
              "constraint": "外键 → users.id"
            }}}},
            "created_at": {{{{
              "type": "datetime",
              "example": "2024-01-15T10:30:00Z"
            }}}}
          }}}},
          "relations": {{{{
            "belongs_to": "users",
            "has_many": ["order_items", "payments"]
          }}}}
        }}}}
      }}}}
    }}}},
    "properties": {{{{
      "audit_fields": {{{{
        "description": "审计字段组",
        "fields": {{{{
          "created_at": {{{{"type": "datetime", "description": "创建时间"}}}},
          "updated_at": {{{{"type": "datetime", "description": "更新时间"}}}}
        }}}},
        "used_by": ["orders", "users", "products"],
        "naming_variants": {{{{
          "updated_at": ["update_at", "modify_time"]
        }}}}
      }}}}
    }}}},

    "relationships": {{{{}}}}
  }}}},

  "business_logic": {{{{
    "rules": {{{{
      "Rule_Order_Amount_NonNegative": {{{{
        "name": "订单金额非负",
        "type": "invariant",
        "applies_to": ["orders"],
        "conditions": ["total_amount >= 0"],
        "action": "拒绝负数金额订单",
        "why": "财务约束，防止数据错误",
        "confidence": "high",
        "source": "constraint"
      }}}},
      "Rule_Shipped_Cannot_Cancel": {{{{
        "name": "已发货不可取消",
        "type": "constraint",
        "applies_to": ["orders"],
        "conditions": ["status = 'shipped'"],
        "action": "禁止取消操作",
        "why": "物流已发出，取消成本高",
        "confidence": "medium",
        "source": "pattern"
      }}}}
    }}}},

    "flows": {{{{
      "order_lifecycle": {{{{
        "description": "订单生命周期流程",
        "steps": [
          {{{{"step": 1, "actor": "User", "action": "创建订单"}}}},
          {{{{"step": 2, "actor": "User", "action": "完成支付"}}}},
          {{{{"step": 3, "actor": "System", "action": "更新状态为已支付", "validation": "Rule_Order_Amount_NonNegative"}}}},
          {{{{"step": 4, "actor": "Warehouse", "action": "发货"}}}},
          {{{{"step": 5, "actor": "User", "action": "确认收货"}}}}
        ]
      }}}}
    }}}}
  }}}},

  "mappings": {{{{
    "objects": {{{{
      "orders": {{{{
        "source": {{{{
          "type": "postgresql",
          "tables": ["orders"],
          "primary_table": "orders",
          "primary_key": "id"
        }}}},
        "field_mapping": {{{{
          "订单ID": "orders.id",
          "订单状态": "orders.status",
          "订单金额": "orders.total_amount"
        }}}},
        "indexes": {{{{
          "primary": "id",
          "regular": ["user_id", "status", "created_at"]
        }}}}
      }}}}
    }}}},
    "metrics": {{{{
      "GMV": {{{{
        "description": "成交总额",
        "definition": "已完成订单的总金额",
        "calculation": {{{{
          "formula": "SUM(orders.total_amount) WHERE status = 'completed'"
        }}}},
        "why": "电商核心指标，衡量平台规模"
      }}}}
    }}}}
  }}}},

  "uncertainties": [
    {{{{
      "id": "UC_001",
      "entity": "orders.(refund_amount, refund_status)",
      "type": "missing_in_database",
      "severity": "medium",
      "data_source": "inferred",
      "issues": [
        {{{{
          "question": "订单取消后是否需要退款？退款流程是什么？",
          "context": "订单有 cancelled 状态，但未发现退款相关字段"
        }}}}
      ],
      "suggested_action": "确认退款流程，可能需要增加 refund_amount 字段"
    }}}},
    {{{{
      "id": "UC_002",
      "entity": "[pattern] *.(created_by, updated_by, created_at, updated_at)",
      "type": "naming_inconsistency",
      "severity": "low",
      "data_source": "database",
      "affected_tables": ["orders", "users", "products", "order_items"],
      "issues": [
        {{{{
          "question": "审计字段命名不统一",
          "context": "部分表使用 create_by，部分使用 created_by"
        }}}}
      ],
      "suggested_action": "在 schema.properties.audit_fields 中定义标准命名，映射各变体"
    }}}},
    {{{{
      "id": "UC_003",
      "entity": "orders",
      "type": "multiple_issues",
      "severity": "high",
      "data_source": "database",
      "issues": [
        {{{{"type": "relationship_unclear", "question": "与 payments 表的关系不明确，是1:1还是1:N？"}}}},
        {{{{"type": "enum_undefined", "field": "status", "question": "cancelled 状态的触发条件未定义"}}}},
        {{{{"type": "precision_unclear", "field": "total_amount", "question": "金额精度是分还是元？"}}}}
      ],
      "suggested_action": "核心业务表，需优先澄清以上问题"
    }}}}
  ]
}}}}
```

---

# 重要要求

1. **必须为该域的每个表生成一个 class**
2. **必须为每个字段生成一个 attribute**
3. **充分利用字段注释（comment）理解业务含义**
4. **识别状态字段并提取 lifecycle_states**
5. **为重要的类、属性、规则添加 why 说明**
6. **根据业务上下文判断 importance（critical/high/medium/low）**
7. **发现的任何问题、缺失、冲突都记录到 uncertainties**
8. **business_logic.rules 的 confidence 要诚实标注**：
   - high: 有明确的数据库约束支撑
   - medium: 从命名模式或字段注释推断
   - low: 仅基于业务常识猜测
9. **不要遗忘输出properties**
10. **只返回 JSON，不要任何解释文字**
"""

        # 🔥 使用流式 API 避免超时（推荐用于长时间运行的请求）
        full_content = ""
        try:
            async for chunk in model.astream([HumanMessage(content=prompt)]):
                if hasattr(chunk, "content"):
                    full_content += chunk.content
        except Exception as e:
            logger.error(f"❌ 域 {domain_name} 流式调用失败: {str(e)}")
            raise

        ontology_data = self._extract_json_from_text(full_content)

        # V3 格式验证：检查 schema.classes 或顶层 classes
        has_schema_classes = (
            ontology_data
            and "schema" in ontology_data
            and "classes" in ontology_data.get("schema", {})
        )
        has_top_classes = ontology_data and "classes" in ontology_data

        if not ontology_data or (not has_schema_classes and not has_top_classes):
            logger.error(f"❌ 域 {domain_name} 生成失败，AI输出前500字符: {response.content[:500]}")
            return {
                "meta": {},
                "schema": {"classes": {}, "relationships": {}},
                "business_logic": {"rules": {}, "flows": {}},
                "mappings": {"objects": {}, "metrics": {}},
                "uncertainties": [],
            }

        # 加载已有的不确定性数据（从领域文件）
        existing_uncertainties = self._load_high_priority_rules_data(connection_name, domain_name)

        # 合并 AI 生成的 uncertainties 和已有的
        ai_uncertainties = ontology_data.get("uncertainties", [])
        all_uncertainties = existing_uncertainties + ai_uncertainties

        # 返回 V3 格式
        return {
            "meta": ontology_data.get("meta", {}),
            "schema": ontology_data.get("schema", {"classes": {}, "relationships": {}}),
            "business_logic": ontology_data.get("business_logic", {"rules": {}, "flows": {}}),
            "mappings": ontology_data.get("mappings", {"objects": {}, "metrics": {}}),
            "uncertainties": all_uncertainties,
        }

    def _load_high_priority_rules_data(
        self, connection_name: str, domain_name: str
    ) -> List[Dict[str, Any]]:
        """
        加载领域的所有不确定性数据（原样返回，用于保存到本体文件）。

        ✨ 新架构：从领域JSON文件的 uncertainties 字段读取所有不确定性（不仅仅是已解决的）。

        Returns:
            List of uncertainty dictionaries (原始格式，包含所有字段)
        """
        try:
            config = ConfigManager()
            schema_path = config.get("storage.schema_path", "./schema_store")
            user_id = get_current_user_id()

            # ✨ 从领域JSON文件读取（带 user_id 隔离）
            domain_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / "domains"
                / f"{domain_name}.json"
            )
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
            user_id = get_current_user_id()

            # ✨ 新逻辑：从领域JSON文件中读取 uncertainties（带 user_id 隔离）
            domain_file = (
                Path(schema_path)
                / user_id
                / get_safe_connection_path(connection_name)
                / "domains"
                / f"{domain_name}.json"
            )
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
        model_manager,
    ) -> Dict[str, Any]:
        """
        合并所有域的本体（V3 格式 - 产品经理版本）。

        V3 格式特点：
        - schema.classes 使用对象格式（key 为表名）
        - business_logic 包含 rules 和 flows
        - mappings 包含 objects 和 metrics
        - uncertainties 统一记录所有问题/缺失/冲突
        """
        # 合并各域的数据
        merged_classes = {}
        merged_relationships = {}
        merged_properties = {}  # 🔧 新增：共享属性合并
        merged_rules = {}
        merged_flows = {}
        merged_objects = {}
        merged_metrics = {}
        all_uncertainties = []
        domain_metas = []

        for domain_name, ont in domain_ontologies.items():
            # 提取 schema
            schema = ont.get("schema", {})
            classes = schema.get("classes", {})
            relationships = schema.get("relationships", {})
            properties = schema.get("properties", {})  # 🔧 新增：提取共享属性

            # 🔥 嵌套格式合并：classes 应该是 {domain_name: {table_name: {...}}}
            if isinstance(classes, dict):
                # 检测是否已经是嵌套格式（AI 返回了 domain 分组）
                if domain_name in classes:
                    # AI 已经按 domain 分组，直接合并
                    merged_classes.update(classes)
                else:
                    # AI 返回的是扁平格式（旧版），我们手动包装
                    merged_classes[domain_name] = classes
            elif isinstance(classes, list):
                # 兼容旧格式（数组），转换为嵌套格式
                domain_classes = {}
                for c in classes:
                    key = c.get("technical_name", c.get("name", ""))
                    if key:
                        domain_classes[key] = c
                if domain_classes:
                    merged_classes[domain_name] = domain_classes

            # 合并 relationships
            if isinstance(relationships, dict):
                merged_relationships.update(relationships)

            # 🔧 新增：智能合并 properties（需要合并 used_by 列表）
            if isinstance(properties, dict):
                for prop_name, prop_data in properties.items():
                    if prop_name in merged_properties:
                        # 属性已存在，合并 used_by 列表
                        existing_used_by = merged_properties[prop_name].get("used_by", [])
                        new_used_by = prop_data.get("used_by", [])
                        merged_properties[prop_name]["used_by"] = list(
                            set(existing_used_by + new_used_by)
                        )

                        # 合并 naming_variants（如果存在）
                        if "naming_variants" in prop_data:
                            existing_variants = merged_properties[prop_name].get(
                                "naming_variants", {}
                            )
                            new_variants = prop_data.get("naming_variants", {})
                            for field, variants in new_variants.items():
                                if field in existing_variants:
                                    existing_variants[field] = list(
                                        set(existing_variants[field] + variants)
                                    )
                                else:
                                    existing_variants[field] = variants
                            merged_properties[prop_name]["naming_variants"] = existing_variants
                    else:
                        # 新属性，直接添加
                        merged_properties[prop_name] = prop_data

            # 提取 business_logic
            business_logic = ont.get("business_logic", {})
            rules = business_logic.get("rules", {})
            flows = business_logic.get("flows", {})

            if isinstance(rules, dict):
                merged_rules.update(rules)
            if isinstance(flows, dict):
                merged_flows.update(flows)

            # 提取 mappings
            mappings = ont.get("mappings", {})
            objects = mappings.get("objects", {})
            metrics = mappings.get("metrics", {})

            if isinstance(objects, dict):
                merged_objects.update(objects)
            if isinstance(metrics, dict):
                merged_metrics.update(metrics)

            # 合并 uncertainties
            all_uncertainties.extend(ont.get("uncertainties", []))

            # 收集 meta
            if ont.get("meta"):
                domain_metas.append(ont["meta"])

        # 加载业务理解五问答案
        from kode.tools.business_understanding import BusinessUnderstandingTool

        business_tool = BusinessUnderstandingTool()
        business_answers = business_tool.get_answers(connection_name) or {}

        # 🚀 基于业务五问生成核心指标
        # 将 merged_metrics 转为列表格式供 _generate_core_metrics 使用
        metrics_list = [{"name": k, **v} for k, v in merged_metrics.items()]

        # 🔥 嵌套格式：遍历所有 domain 的所有 classes
        classes_list = []
        for domain_classes in merged_classes.values():
            if isinstance(domain_classes, dict):
                for table_name, class_data in domain_classes.items():
                    classes_list.append({"technical_name": table_name, **class_data})

        core_metrics = self._generate_core_metrics(
            business_answers=business_answers,
            derived_metrics=metrics_list,
            classes=classes_list,
            model_manager=model_manager,
        )

        # 📊 计算统计信息（嵌套格式）
        classes_with_lifecycle = 0
        classes_with_why = 0
        critical_classes = 0
        total_attributes = 0
        total_class_count = 0

        for domain_classes in merged_classes.values():
            if isinstance(domain_classes, dict):
                for class_data in domain_classes.values():
                    total_class_count += 1
                    if class_data.get("lifecycle_states"):
                        classes_with_lifecycle += 1
                    if class_data.get("why"):
                        classes_with_why += 1
                    if class_data.get("importance") == "critical":
                        critical_classes += 1
                    total_attributes += len(class_data.get("attributes", {}))

        high_confidence_rules = sum(
            1 for r in merged_rules.values() if r.get("confidence") == "high"
        )

        # 构建 V3 格式输出
        return {
            "version": "3.0",
            "meta": {
                "ontology_name": f"{connection_name}_Ontology",
                "ontology_type": "lightweight",
                "product_name": business_answers.get("product_name", ""),
                "business_model": business_answers.get("business_model", ""),
                "revenue_formula": business_answers.get("revenue_formula", ""),
                "conversion_path": business_answers.get("conversion_path", ""),
                "key_metrics": business_answers.get("key_metrics", ""),
                "created_at": datetime.now().isoformat(),
                "source_connection": connection_name,
                "source_database": database,
                "build_method": "domain_based_parallel_v3",
                "model": model_manager.get_current_model_name(),
                "design_principles": [
                    "应然与实然对齐",
                    "四象限分析",
                    "设计透明（why 字段）",
                    "状态感知（lifecycle_states）",
                    "置信度标注（confidence）",
                ],
                "domains": list(domain_ontologies.keys()),
            },
            "schema": {
                "classes": merged_classes,
                "relationships": merged_relationships,
                "properties": merged_properties,  # 🔧 新增：输出共享属性
            },
            "business_logic": {
                "rules": merged_rules,
                "flows": merged_flows,
            },
            "mappings": {
                "objects": merged_objects,
                "metrics": merged_metrics,
            },
            "core_metrics": core_metrics,
            "uncertainties": all_uncertainties,
            "statistics": {
                "domain_count": len(merged_classes),  # 嵌套格式：domain 数量
                "class_count": total_class_count,  # 总表数量
                "attribute_count": total_attributes,
                "relationship_count": len(merged_relationships),
                "rule_count": len(merged_rules),
                "flow_count": len(merged_flows),
                "metric_count": len(merged_metrics),
                "core_metric_count": len(core_metrics),
                "uncertainty_count": len(all_uncertainties),
                "quality": {
                    "classes_with_lifecycle": classes_with_lifecycle,
                    "classes_with_why": classes_with_why,
                    "critical_classes": critical_classes,
                    "high_confidence_rules": high_confidence_rules,
                },
            },
        }

    def _generate_core_metrics(
        self,
        business_answers: Dict[str, str],
        derived_metrics: List[Dict[str, Any]],
        classes: List[Dict[str, Any]],
        model_manager,
    ) -> List[Dict[str, Any]]:
        """
        基于业务理解五问生成核心业务指标（core_metrics）。

        核心指标来源：
        1. key_metrics: 用户明确指定的核心指标（如 MRR, Churn Rate）
        2. revenue_formula: 收入公式中隐含的指标
        3. conversion_path: 转化路径中的漏斗指标

        Returns:
            核心指标列表，每个指标包含：
            - name: 指标名称
            - description: 业务含义
            - category: 分类（revenue/conversion/engagement/retention）
            - formula: 计算公式（基于现有 classes 和 derived_metrics）
            - dependencies: 依赖的类或衍生指标
            - importance: 重要性（critical/high/medium）
        """
        from langchain_core.messages import HumanMessage

        key_metrics_text = business_answers.get("key_metrics", "")
        revenue_formula = business_answers.get("revenue_formula", "")
        conversion_path = business_answers.get("conversion_path", "")
        product_name = business_answers.get("product_name", "")
        business_model = business_answers.get("business_model", "")

        # 如果没有业务答案，返回空
        if not key_metrics_text and not revenue_formula:
            logger.warning("业务五问答案为空，跳过核心指标生成")
            return []

        # 准备 classes 摘要（只取名称和描述）
        class_summary = "\n".join(
            [
                f"- {c.get('name', '')} ({c.get('technical_name', '')}): {c.get('description', '')[:50]}"
                for c in classes[:50]  # 限制数量
            ]
        )

        # 准备衍生指标摘要
        derived_summary = "\n".join(
            [f"- {m.get('name', '')}: {m.get('formula', '')}" for m in derived_metrics[:30]]
        )

        prompt = f"""模拟 SaaS/ERP 业务分析专家。请根据用户的业务上下文，生成核心业务指标（KPIs）。

# 用户业务上下文

**产品**: {product_name}
**商业模式**: {business_model}
**收入公式**: {revenue_formula}
**转化路径**: {conversion_path}
**用户关注的核心指标**: {key_metrics_text}

# 可用的数据类（业务实体）

{class_summary}

# 已有的衍生指标（可复用）

{derived_summary}

# 任务

请根据以上业务上下文，生成 **核心业务指标（Core Metrics / KPIs）**。

**要求**：
1. 必须包含用户明确提到的指标（如 MRR、Churn Rate）
2. 根据收入公式推导相关指标
3. 根据转化路径推导漏斗指标
4. 每个指标必须能通过现有数据类计算（给出具体公式）
5. 指标分类：revenue（营收）、conversion（转化）、engagement（活跃）、retention（留存）

**输出 JSON 格式**：
```json
{{
  "core_metrics": [
    {{
      "name": "MRR (月经常性收入)",
      "description": "每月从订阅用户获得的经常性收入，SaaS核心营收指标",
      "category": "revenue",
      "formula": "SUM(订阅订单.月付金额) WHERE 订阅状态='活跃'",
      "dependencies": ["订阅订单", "平台用户"],
      "importance": "critical",
      "calculation_notes": "需要从订单表筛选订阅类型订单，按月汇总"
    }},
    {{
      "name": "Churn Rate (流失率)",
      "description": "每月流失的付费用户占比，衡量用户留存的核心指标",
      "category": "retention",
      "formula": "(期初付费用户数 - 期末付费用户数) / 期初付费用户数 * 100%",
      "dependencies": ["用户", "订阅订单"],
      "importance": "critical",
      "calculation_notes": "需要按月追踪用户订阅状态变化"
    }},
    {{
      "name": "付费转化率",
      "description": "注册用户中成功付费的比例",
      "category": "conversion",
      "formula": "付费用户数 / 注册用户数 * 100%",
      "dependencies": ["用户", "订单"],
      "importance": "high",
      "calculation_notes": "使用 top_up_tag 或 subscription_tag 判断是否付费"
    }}
  ]
}}
```

**只返回 JSON，不要解释文字。**
"""

        try:
            model = model_manager.get_model("main")
            model.temperature = 0.0
            model.max_tokens = 8000

            response = model.invoke([HumanMessage(content=prompt)])
            result = self._extract_json_from_text(response.content)

            if result and "core_metrics" in result:
                logger.info(f"✅ 生成了 {len(result['core_metrics'])} 个核心指标")
                return result["core_metrics"]
            else:
                logger.warning(f"核心指标生成失败，AI输出: {response.content[:500]}")
                return []

        except Exception as e:
            logger.error(f"核心指标生成异常: {e}")
            return []


class OntologySearchTool(KodeTool):
    """
    Search ontology for concepts, properties, and relationships.

    Supports semantic, exact, and fuzzy search.
    """

    name: str = "OntologySearch"
    description: str = """Search stored ontology for concepts, properties, and relationships.

    **USAGE**: Pass the connection_name directly (e.g., 'yanfa').
    The tool will automatically find the ontology file (ontology.json).

    Examples:
    - ontology_path='yanfa' → searches ontology_store/yanfa/ontology.json
    - ontology_path='ontology_store/yanfa' → also works

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
            ontology_path: Path to ontology storage DIRECTORY (e.g., 'ontology_store/yanfa')
                          OR connection_name directly (e.g., 'yanfa')
            query: Search query
            search_type: Type of search
            top_k: Number of results

        Returns:
            Search results as JSON
        """
        try:
            config = ConfigManager()
            ontology_base = config.get("storage.ontology_path", "./ontology_store")
            # 🔑 获取 user_id 用于路径隔离
            from kode.utils.context import get_current_user_id

            user_id = get_current_user_id()

            # 🔍 智能路径检测和纠正
            ontology_path_obj = Path(ontology_path)

            # 情况0：直接传入 connection_name（如 "yanfa"）
            if (
                not ontology_path_obj.exists()
                and "/" not in ontology_path
                and "\\" not in ontology_path
            ):
                # 尝试作为 connection_name 处理（包含 user_id 隔离）
                corrected_path = Path(ontology_base) / user_id / ontology_path
                if corrected_path.exists():
                    logger.info(f"✅ 识别为 connection_name: {ontology_path} → {corrected_path}")
                    ontology_path_obj = corrected_path

            # 检测常见错误：传入了文件路径而非目录
            if ontology_path_obj.suffix == ".json":
                # 用户传入了文件路径，尝试自动纠正
                logger.warning(f"⚠️ OntologySearch: 检测到文件路径 {ontology_path}，自动纠正为目录")

                # 情况1：传入的是 schema_store/.../xxx.json → 应该是 ontology_store/{user_id}/connection_name
                if "schema_store" in str(ontology_path):
                    # 提取 connection_name (schema_store/{user_id}/{connection_name}/... 或 schema_store/{connection_name}/...)
                    parts = ontology_path_obj.parts
                    if len(parts) >= 2 and "schema_store" in parts:
                        schema_idx = parts.index("schema_store")
                        if schema_idx + 2 < len(parts):
                            # 假设是 schema_store/{user_id}/{connection_name}
                            connection_name = parts[schema_idx + 2]
                        elif schema_idx + 1 < len(parts):
                            # 兼容旧版 schema_store/{connection_name}
                            connection_name = parts[schema_idx + 1]
                        else:
                            connection_name = None

                        if connection_name:
                            # 纠正路径（包含 user_id）
                            corrected_path = Path(ontology_base) / user_id / connection_name
                            logger.info(
                                f"✅ 自动纠正: schema 路径 → ontology 路径 {corrected_path}"
                            )
                            ontology_path_obj = corrected_path

                # 情况2：传入的是 ontology_store/.../ontology_*.json → 提取目录
                elif "ontology_store" in str(ontology_path):
                    ontology_path_obj = ontology_path_obj.parent
                    logger.info(f"✅ 自动纠正: 文件路径 → 目录路径 {ontology_path_obj}")

            # 使用统一的本体文件
            ontology_file = ontology_path_obj / "ontology.json"

            if not ontology_file.exists():
                # 生成友好的错误消息
                error_msg = f"本体文件未找到"

                # 检查是否是路径错误
                if "schema_store" in str(ontology_path):
                    error_msg += (
                        "\n\n❌ 错误原因: 你传入的是 schema 文件路径，而不是 ontology 目录！"
                    )
                    error_msg += "\n\n✅ 正确用法: ontology_path 应该是 'ontology_store/{connection_name}' 或直接传入 connection_name，例如："
                    error_msg += "\n  - 正确: 'ontology_store/yanfa' 或 'yanfa'"
                    error_msg += "\n  - 错误: 'schema_store/yanfa/domains/order_management.json'"
                else:
                    error_msg += f"\n\n💡 提示: 请确保已运行 OntologyBuilder 工具生成本体。"
                    error_msg += f"\n  期望目录: {ontology_path_obj}"
                    error_msg += f"\n  期望文件: {ontology_file}"

                return json.dumps(
                    {
                        "status": "error",
                        "message": error_msg,
                        "provided_path": str(ontology_path),
                        "expected_directory": str(ontology_path_obj),
                        "expected_file": str(ontology_file),
                    },
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(f"✅ 使用本体文件: {ontology_file}")

            with open(ontology_file, "r", encoding="utf-8") as f:
                ontology_data = json.load(f)

            # V2 格式：直接就是本体数据
            ontology = ontology_data
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
            results = self._semantic_search(ontology, query, top_k, str(ontology_path_obj))

            # 提取 uncertainties（完整列表）
            uncertainties = ontology.get("uncertainties", [])

            # 从搜索结果中提取实体 key 列表
            matched_class_keys = set()
            for cls in results.get("classes", []):
                class_key = cls.get("key", "")
                if class_key:
                    matched_class_keys.add(class_key)
                    # 也提取表名部分（去掉 domain 前缀）
                    if "." in class_key:
                        table_name = class_key.split(".", 1)[1]
                        matched_class_keys.add(table_name)

            # 筛选与搜索结果实体相关的不确定性
            entity_related_uncertainties = []
            for uncertainty in uncertainties:
                # 跳过已解决的
                if uncertainty.get("status") == "resolved":
                    continue

                entity = uncertainty.get("entity", "")
                domain = uncertainty.get("domain", "")

                # 检查是否与搜索到的 class 相关
                is_related = False
                for class_key in matched_class_keys:
                    # 1. entity 完全匹配表名
                    if entity == class_key:
                        is_related = True
                        break
                    # 2. entity 包含表名（如 "platform_user.id vs platform_user_account.user_id"）
                    if class_key in entity:
                        is_related = True
                        break
                    # 3. class_key 是 domain.table 格式，检查 domain 匹配
                    if "." in class_key:
                        cls_domain, cls_table = class_key.split(".", 1)
                        if domain == cls_domain and cls_table in entity:
                            is_related = True
                            break

                if is_related:
                    # 返回精简版不确定性（去掉冗余字段）
                    entity_related_uncertainties.append(
                        {
                            "id": uncertainty.get("id", ""),
                            "type": uncertainty.get("type", ""),
                            "category": uncertainty.get("category", ""),
                            "priority": uncertainty.get("priority", ""),
                            "entity": entity,
                            "question": uncertainty.get("question", ""),
                            "impact": uncertainty.get("impact", ""),
                            "suggestions": uncertainty.get("suggestions", []),
                        }
                    )

            # 提取 meta 业务信息（V3 格式特有）
            meta_info = ontology.get("meta", {})
            business_context = {}
            if meta_info:
                # 提取关键业务字段
                business_context = {
                    "product_name": meta_info.get("product_name", ""),
                    "business_model": meta_info.get("business_model", ""),
                    "revenue_formula": meta_info.get("revenue_formula", ""),
                    "conversion_path": meta_info.get("conversion_path", ""),
                    "key_metrics": meta_info.get("key_metrics", ""),
                }
                # 移除空值字段
                business_context = {k: v for k, v in business_context.items() if v}

            # Return with related uncertainties content
            ontology_version = ontology.get("version", "2.0")
            response_data = {
                "status": "success",
                "query": query,
                "search_type": search_type,
                "results": results,  # Keep search results (usually small)
                "ontology_version": ontology_version,
                "ontology_file": str(ontology_file),
                "uncertainties": {
                    "related_to_results": entity_related_uncertainties,  # 与搜索结果实体相关的不确定性
                    "related_count": len(entity_related_uncertainties),
                    "unresolved_count": len(
                        [u for u in uncertainties if u.get("status") != "resolved"]
                    ),
                    "total_count": len(uncertainties),
                    "resolved_count": len(
                        [u for u in uncertainties if u.get("status") == "resolved"]
                    ),
                },
            }

            # 如果有业务上下文信息，添加到响应中
            if business_context:
                response_data["business_context"] = business_context

            return json.dumps(
                response_data,
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
            if (
                query in concept_name.lower()
                or query in concept_data.get("business_name", "").lower()
            ):
                results["concepts"].append(concept_data)

        # Search properties
        for prop_key, prop_data in ontology.get("properties", {}).items():
            if query in prop_key.lower() or query in prop_data.get("business_name", "").lower():
                results["properties"].append(prop_data)

        return results

    def _fuzzy_search(self, ontology: Dict[str, Any], query: str, top_k: int) -> Dict[str, List]:
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
                concept_data.get("domain", ""),
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
                prop_data.get("domain", ""),
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

    def _expand_query(self, query: str) -> str:
        """
        业务术语同义词扩展，提高语义搜索召回率。

        Args:
            query: 原始查询

        Returns:
            扩展后的查询
        """
        # 业务同义词映射
        synonyms = {
            "GMV": "交易金额 成交额 订单金额 payment_price revenue",
            "订单": "order 交易 购买",
            "支付": "payment pay 付款 paid",
            "用户": "user 会员 customer",
            "充值": "recharge top_up 续费",
            "收入": "revenue income MRR ARR",
            "金额": "amount price money",
            "交易": "transaction trade order",
        }

        expanded = query
        query_lower = query.lower()
        for term, expansion in synonyms.items():
            if term.lower() in query_lower or term in query:
                expanded += f" {expansion}"

        return expanded

    def _rerank_by_keywords(
        self,
        result_ids: List[str],
        result_distances: List[float],
        query: str,
        class_by_key: Dict[str, Any],
    ) -> List[str]:
        """
        使用关键词匹配对语义搜索结果重排序。

        Args:
            result_ids: ChromaDB 返回的 ID 列表
            result_distances: ChromaDB 返回的距离列表
            query: 原始查询
            class_by_key: 类索引

        Returns:
            重排后的 ID 列表
        """
        query_terms = set(query.lower().split())
        scored = []

        for class_id, distance in zip(result_ids, result_distances):
            # 语义分数（距离越小越好，转换为分数）
            semantic_score = 1 - distance

            # 关键词匹配分数
            keyword_score = 0
            class_text = class_id.lower()

            # 检查 class_id 是否包含查询词
            for term in query_terms:
                if term in class_text:
                    keyword_score += 0.3

            # 检查 description 是否包含查询词
            if class_id in class_by_key:
                desc = class_by_key[class_id].get("description", "").lower()
                why = class_by_key[class_id].get("why", "").lower()
                for term in query_terms:
                    if term in desc:
                        keyword_score += 0.2
                    if term in why:
                        keyword_score += 0.15

            # 综合分数
            total_score = semantic_score + keyword_score
            scored.append((class_id, total_score))

        # 按分数排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored]

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
                path=str(chroma_dir), settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collections for concepts and properties
            concepts_collection = client.get_or_create_collection(
                name="ontology_concepts", metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )

            properties_collection = client.get_or_create_collection(
                name="ontology_properties", metadata={"hnsw:space": "cosine"}
            )

            # 🔥 检查索引版本，如果是旧版本则重建
            # 使用 collection metadata 存储版本号
            CURRENT_INDEX_VERSION = "v2_with_why"  # 增加版本号以强制重建索引
            needs_reindex = False

            if concepts_collection.count() == 0:
                needs_reindex = True
            else:
                # 检查版本标记（通过尝试获取第一个文档的 metadata）
                try:
                    peek = concepts_collection.peek(limit=1)
                    if peek and peek.get("metadatas") and peek["metadatas"]:
                        first_meta = peek["metadatas"][0]
                        if first_meta.get("index_version") != CURRENT_INDEX_VERSION:
                            needs_reindex = True
                            logger.info(f"Index version mismatch, will reindex")
                except Exception:
                    needs_reindex = True

            if needs_reindex:
                # 删除旧的 collections 并重建
                try:
                    client.delete_collection("ontology_concepts")
                    client.delete_collection("ontology_properties")
                except Exception:
                    pass

                concepts_collection = client.get_or_create_collection(
                    name="ontology_concepts", metadata={"hnsw:space": "cosine"}
                )
                properties_collection = client.get_or_create_collection(
                    name="ontology_properties", metadata={"hnsw:space": "cosine"}
                )
                self._index_ontology_to_chroma(
                    ontology, concepts_collection, properties_collection, CURRENT_INDEX_VERSION
                )

            # 🔥 查询扩展：添加业务同义词
            expanded_query = self._expand_query(query)

            # 🔥 获取 2 倍候选用于重排
            search_k = min(top_k * 2, 30)  # 最多获取 30 个候选

            # Search concepts
            concept_count = concepts_collection.count()
            concept_results = None
            if concept_count > 0:
                concept_results = concepts_collection.query(
                    query_texts=[expanded_query],
                    n_results=min(search_k, concept_count),
                    include=["distances"],  # 需要距离用于重排
                )

            # Search properties
            property_count = properties_collection.count()
            property_results = None
            if property_count > 0:
                property_results = properties_collection.query(
                    query_texts=[expanded_query],
                    n_results=min(search_k, property_count),
                    include=["distances"],
                )

            # Parse results and retrieve full ontology data
            # 支持 V1 (concepts/properties)、V2 (classes 数组) 和 V3 (schema.classes 对象) 三种格式
            results: Dict[str, List] = {
                "concepts": [],
                "properties": [],
                "relationships": [],
                "classes": [],
            }

            # 检测格式并获取 classes
            classes_data = None
            is_dict_format = False

            # V3 格式：schema.classes 对象
            if "schema" in ontology and "classes" in ontology.get("schema", {}):
                classes_data = ontology["schema"]["classes"]
                is_dict_format = isinstance(classes_data, dict)
            # V2 格式：classes 数组
            elif "classes" in ontology:
                classes_data = ontology["classes"]
                is_dict_format = isinstance(classes_data, dict)

            if classes_data:
                # 🔥 检测是否是嵌套格式（domain → table_name）
                is_nested = False
                if is_dict_format and classes_data:
                    # 检查第一个 key 的 value 是否也是 dict of classes
                    first_val = next(iter(classes_data.values()), None)
                    if isinstance(first_val, dict) and any(
                        isinstance(v, dict) and "attributes" in v for v in first_val.values()
                    ):
                        is_nested = True

                # 构建 class 索引（用于快速查找）
                class_by_key = {}
                class_by_name = {}

                if is_nested:
                    # 🔥 嵌套格式：遍历所有 domain 的所有 classes
                    for domain_name, domain_classes in classes_data.items():
                        if isinstance(domain_classes, dict):
                            for table_name, class_data in domain_classes.items():
                                # ID 格式: "domain_name.table_name"
                                class_id = f"{domain_name}.{table_name}"
                                class_by_key[class_id] = class_data
                                if class_data.get("description"):
                                    class_by_name[class_data.get("description", "")[:50]] = (
                                        class_id,
                                        class_data,
                                    )
                elif is_dict_format:
                    # 扁平对象格式：key 是表名
                    class_by_key = classes_data
                    for key, val in classes_data.items():
                        if isinstance(val, dict) and val.get("description"):
                            class_by_name[val.get("description", "")[:50]] = (key, val)
                else:
                    # V2 数组格式
                    class_by_key = {
                        c.get("technical_name", c.get("name", "")): c for c in classes_data
                    }
                    class_by_name = {c.get("name", ""): c for c in classes_data}

                # ✨ 使用集合去重，避免重复添加同一个类
                added_class_ids = set()

                # 🔥 重排序：使用关键词匹配对语义搜索结果重排
                reranked_concept_ids = []
                if concept_results and concept_results["ids"] and concept_results["ids"][0]:
                    distances = concept_results.get("distances", [[]])[0]
                    if distances:
                        reranked_concept_ids = self._rerank_by_keywords(
                            concept_results["ids"][0], distances, query, class_by_key
                        )
                    else:
                        reranked_concept_ids = concept_results["ids"][0]

                # Add classes from concept results (after reranking)
                for class_id in reranked_concept_ids[:top_k]:
                    if class_id not in added_class_ids:
                        if class_id in class_by_key:
                            # 精简返回结果，传入 query 用于相关性过滤
                            slim_class = self._slim_class_for_search(
                                class_id, class_by_key[class_id], query
                            )
                            results["classes"].append(slim_class)
                            added_class_ids.add(class_id)

                # Add classes from property results (find parent class)
                if property_results and property_results["ids"] and property_results["ids"][0]:
                    for prop_id in property_results["ids"][0]:
                        # 🔥 嵌套格式 prop_id: "domain.table.column"
                        # 扁平格式 prop_id: "table.column"
                        parts = prop_id.split(".")

                        if is_nested and len(parts) >= 2:
                            # 嵌套格式：domain.table.column → class_id = "domain.table"
                            class_id = f"{parts[0]}.{parts[1]}"
                        elif len(parts) >= 1:
                            # 扁平格式：table.column → class_id = "table"
                            class_id = parts[0]
                        else:
                            continue

                        if class_id not in added_class_ids:
                            if class_id in class_by_key:
                                # 精简返回结果，传入 query 用于相关性过滤
                                slim_class = self._slim_class_for_search(
                                    class_id, class_by_key[class_id], query
                                )
                                results["classes"].append(slim_class)
                                added_class_ids.add(class_id)
                                if len(results["classes"]) >= top_k:
                                    break

                # 🔥 精确匹配兜底：确保关键词直接匹配的表不被漏掉
                query_terms = set(query.lower().split())
                for class_id in class_by_key:
                    if len(results["classes"]) >= top_k:
                        break
                    if class_id in added_class_ids:
                        continue

                    class_data = class_by_key[class_id]
                    class_text = class_id.lower()
                    desc = class_data.get("description", "").lower()

                    # 检查 class_id 或 description 是否包含查询关键词
                    matched = False
                    for term in query_terms:
                        if len(term) >= 2 and (term in class_text or term in desc):
                            matched = True
                            break

                    if matched:
                        slim_class = self._slim_class_for_search(class_id, class_data, query)
                        results["classes"].append(slim_class)
                        added_class_ids.add(class_id)

            # V1 格式：concepts/properties 字典
            elif "concepts" in ontology:
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

    def _slim_class_for_search(
        self, class_id: str, class_data: Dict[str, Any], query: str = ""
    ) -> Dict[str, Any]:
        """
        精简 class 返回结果，大幅减少 token 消耗。

        策略：
        1. 与查询相关的字段：保留 type + why（完整信息）
        2. 主键/外键：只显示 "字段名(类型)" 格式
        3. 其他字段：只显示总数量
        """
        slim = {
            "key": class_id,
            "description": class_data.get("description", ""),
        }

        # 只在重要时显示 importance
        importance = class_data.get("importance", "")
        if importance in ("critical", "important"):
            slim["importance"] = importance

        # 构建查询关键词集合（支持中英文）
        query_keywords = set()
        if query:
            query_lower = query.lower()
            for word in query_lower.split():
                if len(word) >= 2:
                    query_keywords.add(word)

        if "attributes" in class_data and class_data["attributes"]:
            related_attrs = {}  # 与查询相关的字段
            pk_fk_list = []  # 主键/外键列表（紧凑格式）
            other_count = 0  # 其他字段数量

            for attr_name, attr_info in class_data["attributes"].items():
                if not isinstance(attr_info, dict):
                    other_count += 1
                    continue

                attr_name_lower = attr_name.lower()
                attr_why = attr_info.get("why", "").lower()
                constraint = attr_info.get("constraint", "")
                attr_type = attr_info.get("type", "unknown")

                # 判断是否与查询相关
                is_related = False
                for kw in query_keywords:
                    if kw in attr_name_lower or kw in attr_why:
                        is_related = True
                        break

                # 判断是否是主键/外键
                is_pk = "主键" in constraint or "primary" in constraint.lower()
                is_fk = "外键" in constraint or "→" in constraint

                if is_related:
                    # 查询相关：保留完整信息
                    related_attrs[attr_name] = {
                        "type": attr_type,
                        "why": attr_info.get("why", ""),
                    }
                elif is_pk or is_fk:
                    # 主键/外键：紧凑格式
                    if is_pk:
                        pk_fk_list.append(f"{attr_name}(PK)")
                    elif "→" in constraint:
                        fk_ref = constraint.split("→")[-1].strip().split(",")[0].strip()
                        pk_fk_list.append(f"{attr_name}→{fk_ref}")
                    else:
                        pk_fk_list.append(f"{attr_name}(FK)")
                else:
                    other_count += 1

            # 组装精简的 attributes
            if related_attrs or pk_fk_list or other_count > 0:
                slim["attributes"] = {}
                if related_attrs:
                    slim["attributes"]["related"] = related_attrs
                if pk_fk_list:
                    slim["attributes"]["keys"] = pk_fk_list
                if other_count > 0:
                    slim["attributes"]["other_fields_count"] = other_count

        # relations 也精简
        if "relations" in class_data and class_data["relations"]:
            relations = class_data["relations"]
            slim_relations = []
            for rel_type, rel_target in relations.items():
                if isinstance(rel_target, list):
                    slim_relations.append(f"{rel_type}: {', '.join(rel_target)}")
                else:
                    slim_relations.append(f"{rel_type}: {rel_target}")
            if slim_relations:
                slim["relations"] = slim_relations

        return slim

    def _index_ontology_to_chroma(
        self,
        ontology: Dict[str, Any],
        concepts_collection,
        properties_collection,
        index_version: str = "v1",
    ):
        """
        Index ontology data into ChromaDB collections.
        支持 V1 (concepts/properties)、V2 (classes 数组) 和 V3 (schema.classes 对象) 三种格式。

        Args:
            ontology: Ontology data structure
            concepts_collection: ChromaDB collection for concepts/classes
            properties_collection: ChromaDB collection for properties
            index_version: 索引版本号，用于判断是否需要重建索引
        """
        concept_ids = []
        concept_docs = []
        concept_metadatas = []
        property_ids = []
        property_docs = []
        property_metadatas = []

        # 检测格式并获取 classes
        classes_data = None
        is_dict_format = False

        # V3 格式：schema.classes 对象
        if "schema" in ontology and "classes" in ontology.get("schema", {}):
            classes_data = ontology["schema"]["classes"]
            is_dict_format = isinstance(classes_data, dict)
        # V2 格式：classes（可能是数组或对象）
        elif "classes" in ontology:
            classes_data = ontology["classes"]
            is_dict_format = isinstance(classes_data, dict)

        if classes_data:
            # 🔥 检测是否是嵌套格式（domain → table_name）
            is_nested = False
            if is_dict_format and classes_data:
                first_val = next(iter(classes_data.values()), None)
                if isinstance(first_val, dict) and any(
                    isinstance(v, dict) and "attributes" in v for v in first_val.values()
                ):
                    is_nested = True

            # 统一处理：转换为 (key, data) 对的列表
            class_items = []
            if is_nested:
                # 🔥 嵌套格式：遍历所有 domain 的所有 classes
                for domain_name, domain_classes in classes_data.items():
                    if isinstance(domain_classes, dict):
                        for table_name, class_data in domain_classes.items():
                            # ID 格式: "domain_name.table_name"
                            class_id = f"{domain_name}.{table_name}"
                            class_items.append((class_id, class_data))
            elif is_dict_format:
                # V3 扁平对象格式：key 是表名
                class_items = list(classes_data.items())
            else:
                # V2 数组格式
                class_items = [
                    (c.get("technical_name", c.get("name", f"class_{i}")), c)
                    for i, c in enumerate(classes_data)
                ]

            for class_key, class_data in class_items:
                if not class_key:
                    continue

                # 用 key 作为 ID
                class_id = class_key
                concept_ids.append(class_id)

                # Create rich text representation for embedding
                # V3 格式用 attributes（对象），V2 格式用 properties（数组）
                attributes = class_data.get("attributes", {})
                properties = class_data.get("properties", [])

                if isinstance(attributes, dict):
                    # V3: attributes 是对象
                    attr_names = " ".join(attributes.keys())
                    attr_descs = " ".join(
                        [
                            str(v.get("constraint", ""))[:30]
                            for v in attributes.values()
                            if isinstance(v, dict) and v.get("constraint")
                        ]
                    )
                    # 🔥 提取关键业务字段的 why（用于提高语义搜索召回率）
                    key_attr_whys = []
                    importance_keywords = [
                        "核心",
                        "关键",
                        "重要",
                        "收入",
                        "订单",
                        "GMV",
                        "MRR",
                        "金额",
                        "支付",
                        "交易",
                    ]
                    for attr_name, attr_data in attributes.items():
                        if isinstance(attr_data, dict):
                            why = attr_data.get("why", "")
                            if why and any(kw in why for kw in importance_keywords):
                                key_attr_whys.append(f"{attr_name}:{why[:50]}")
                    key_whys_text = " ".join(key_attr_whys[:5])  # 限制最多 5 个关键字段
                else:
                    # V2: properties 是数组
                    attr_names = " ".join([p.get("name", "") for p in properties])
                    attr_descs = " ".join(
                        [p.get("description", "")[:30] for p in properties if p.get("description")]
                    )
                    key_whys_text = ""

                doc_text = f"{class_key} {class_data.get('description', '')} {class_data.get('why', '')} {attr_names} {attr_descs} {key_whys_text}"
                concept_docs.append(doc_text)

                concept_metadatas.append(
                    {
                        "key": class_key,
                        "description": class_data.get("description", "")[:100],
                        "importance": class_data.get("importance", ""),
                        "index_version": index_version,  # 🔥 添加版本号用于判断是否需要重建
                    }
                )

                # Index attributes/properties within this class
                if isinstance(attributes, dict):
                    # V3: attributes 是对象
                    for attr_name, attr_data in attributes.items():
                        if not attr_name:
                            continue

                        prop_id = f"{class_id}.{attr_name}"
                        property_ids.append(prop_id)

                        attr_info = attr_data if isinstance(attr_data, dict) else {}
                        # 🔥 加入 why 字段，提高业务语义召回率
                        attr_why = attr_info.get("why", "")[:60] if attr_info.get("why") else ""
                        doc_text = f"{attr_name} {attr_info.get('type', '')} {attr_info.get('constraint', '')} {attr_why} {class_key}"
                        property_docs.append(doc_text)

                        property_metadatas.append(
                            {
                                "attribute_name": attr_name,
                                "class_key": class_key,
                                "type": attr_info.get("type", ""),
                            }
                        )
                else:
                    # V2: properties 是数组
                    for prop in properties:
                        prop_name = prop.get("name", "")
                        prop_tech = prop.get("technical_name", prop.get("column_mapping", ""))
                        if not prop_name and not prop_tech:
                            continue

                        prop_id = f"{class_id}.{prop_name or prop_tech}"
                        property_ids.append(prop_id)

                        doc_text = (
                            f"{prop_name} {prop_tech} {prop.get('description', '')} {class_key}"
                        )
                        property_docs.append(doc_text)

                        property_metadatas.append(
                            {
                                "property_name": prop_name,
                                "technical_name": prop_tech,
                                "class_key": class_key,
                                "type": prop.get("type", ""),
                            }
                        )

        # V1 格式：concepts/properties 字典
        elif "concepts" in ontology:
            for concept_name, concept_data in ontology.get("concepts", {}).items():
                concept_ids.append(concept_name)

                doc_text = f"{concept_data.get('business_name_cn', '')} {concept_data.get('business_name_en', '')} {concept_data.get('description', '')} {concept_data.get('domain', '')}"
                concept_docs.append(doc_text)

                concept_metadatas.append(
                    {
                        "technical_name": concept_name,
                        "business_name": concept_data.get("business_name_cn", ""),
                        "domain": concept_data.get("domain", ""),
                    }
                )

            for prop_key, prop_data in ontology.get("properties", {}).items():
                property_ids.append(prop_key)

                doc_text = f"{prop_data.get('business_name_cn', '')} {prop_data.get('business_name_en', '')} {prop_data.get('description', '')} {prop_data.get('domain', '')}"
                property_docs.append(doc_text)

                property_metadatas.append(
                    {
                        "property_key": prop_key,
                        "business_name": prop_data.get("business_name_cn", ""),
                        "domain": prop_data.get("domain", ""),
                    }
                )

        # Add to collections
        if concept_ids:
            concepts_collection.add(
                ids=concept_ids, documents=concept_docs, metadatas=concept_metadatas
            )

        if property_ids:
            properties_collection.add(
                ids=property_ids, documents=property_docs, metadatas=property_metadatas
            )

        logger.info(
            f"Indexed {len(concept_ids)} classes/concepts and {len(property_ids)} properties to ChromaDB"
        )
