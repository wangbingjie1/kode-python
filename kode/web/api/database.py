"""
Database Management API Routes

REST endpoints for database connection management, schema extraction,
and ontology operations.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from pathlib import Path
import json
import asyncio
from functools import partial
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kode.schemas.database import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
    DatabaseConnectionResponse,
    DatabaseTestResult,
    DatabaseSchemaResponse,
    OntologyResponse,
    OntologySearchQuery,
    OntologySearchResult,
    OntologyExportRequest,
)
from fastapi.responses import Response
import csv
import io
from kode.services.database_manager import (
    DatabaseConnection,
    DatabaseConnectionManager,
    db_manager,
)
from kode.database.session import get_db
from kode.models import User, DatabaseConnectionModel
from kode.web.dependencies import get_current_user
from kode.utils.logger import setup_logger
from kode.core.security import encrypt_db_password, decrypt_db_password

router = APIRouter()
logger = setup_logger(__name__)


@router.post(
    "/connections",
    response_model=DatabaseConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    connection_data: DatabaseConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new database connection"""
    try:
        # 检查该用户是否已有同名连接
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == connection_data.name
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"连接名称 '{connection_data.name}' 已存在"
            )

        # Create ORM model instance
        db_connection = DatabaseConnectionModel(
            user_id=current_user.id,
            name=connection_data.name,
            db_type=connection_data.db_type,
            host=connection_data.host,
            port=connection_data.port,
            database=connection_data.database,
            username=connection_data.username,
            password=encrypt_db_password(connection_data.password),
            db_schema=connection_data.db_schema,
            ssl=connection_data.ssl,
        )

        db.add(db_connection)
        await db.commit()
        await db.refresh(db_connection)

        # 添加到内存管理器（使用 user_id:name 作为唯一标识）
        connection_key = f"{current_user.id}:{connection_data.name}"
        connection = DatabaseConnection(
            name=connection_key,  # 内存中使用带用户前缀的名称
            db_type=connection_data.db_type,
            host=connection_data.host,
            port=connection_data.port,
            database=connection_data.database,
            username=connection_data.username,
            password=connection_data.password,
            db_schema=connection_data.db_schema,
            ssl=connection_data.ssl,
        )
        db_manager.add_connection(connection)

        logger.info(f"User {current_user.username} created connection: {connection_data.name}")
        return DatabaseConnectionResponse(**db_connection.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}",
        )


@router.get("/connections", response_model=List[DatabaseConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all database connections for current user"""
    try:
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id
            )
        )
        connections = result.scalars().all()

        return [DatabaseConnectionResponse(**conn.to_dict()) for conn in connections]

    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}",
        )


@router.get("/connections/{name}", response_model=DatabaseConnectionResponse)
async def get_connection(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific database connection"""
    try:
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        return DatabaseConnectionResponse(**connection.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection: {str(e)}",
        )


@router.put("/connections/{name}", response_model=DatabaseConnectionResponse)
async def update_connection(
    name: str,
    update_data: DatabaseConnectionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a database connection"""
    try:
        # Get existing connection
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        # Close existing engines (从内存管理器中删除)
        connection_key = f"{current_user.id}:{name}"
        await db_manager.close_connection_async(connection_key)
        db_manager.remove_connection(connection_key)

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(existing, key) and key != 'user_id':  # 不允许修改 user_id
                # 密码字段需要加密
                if key == 'password' and value:
                    setattr(existing, key, encrypt_db_password(value))
                else:
                    setattr(existing, key, value)

        await db.commit()
        await db.refresh(existing)

        # 重新添加到内存管理器（需要解密密码）
        try:
            decrypted_password = decrypt_db_password(existing.password)
        except Exception:
            # 如果解密失败，可能是旧数据
            decrypted_password = existing.password

        connection = DatabaseConnection(
            name=connection_key,
            db_type=existing.db_type,
            host=existing.host,
            port=existing.port,
            database=existing.database,
            username=existing.username,
            password=decrypted_password,
            db_schema=existing.db_schema,
            ssl=existing.ssl,
        )
        db_manager.add_connection(connection)

        logger.info(f"User {current_user.username} updated connection: {name}")
        return DatabaseConnectionResponse(**existing.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update connection: {str(e)}",
        )


@router.delete("/connections/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a database connection"""
    try:
        # Check if connection exists
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        # Close engines first (async version)
        connection_key = f"{current_user.id}:{name}"
        await db_manager.close_connection_async(connection_key)

        # Remove from in-memory manager
        db_manager.remove_connection(connection_key)

        # Remove from database
        await db.delete(connection)
        await db.commit()

        logger.info(f"User {current_user.username} deleted connection: {name}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}",
        )


@router.post("/connections/{name}/test", response_model=DatabaseTestResult)
async def test_connection(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test a database connection"""
    try:
        # 验证用户是否拥有该连接
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found"
            )

        # Test connection
        connection_key = f"{current_user.id}:{name}"
        test_result = await db_manager.test_connection_async(connection_key)

        if test_result["status"] == "error":
            return DatabaseTestResult(
                status="error",
                message=test_result["message"],
                error=test_result.get("error"),
            )

        return DatabaseTestResult(
            status="success",
            message=test_result["message"],
            connection=DatabaseConnectionResponse(**test_result["connection"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return DatabaseTestResult(
            status="error",
            message=f"Failed to test connection: {str(e)}",
            error=str(e),
        )


def _extract_schema_sync(name: str) -> Dict[str, Any]:
    """
    Synchronous schema extraction function to run in thread pool.

    Args:
        name: Connection name

    Returns:
        Dict with schema information
    """
    # Get a fresh engine with extended timeout settings
    from sqlalchemy import create_engine, text

    connection = db_manager.get_connection(name)
    if not connection:
        raise ValueError(f"Connection '{name}' not found")

    # Create engine with increased timeout and pool settings
    url = connection.get_connection_url(async_mode=False)

    # Configure connection arguments based on database type
    connect_args = {}
    if connection.db_type == "mysql":
        connect_args = {
            "connect_timeout": 60,  # 60 seconds to establish connection
            "read_timeout": 120,    # 120 seconds to read response
            "write_timeout": 120,   # 120 seconds to write data
        }

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections after 1 hour
        connect_args=connect_args
    )

    try:
        # Test connection first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Get inspector from the fresh engine
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)

        # Extract schema with progress logging
        tables = []
        table_names = inspector.get_table_names()
        logger.info(f"Extracting schema for {len(table_names)} tables from '{name}'")

        for idx, table_name in enumerate(table_names):
            try:
                if idx % 10 == 0:
                    logger.info(f"Processing table {idx + 1}/{len(table_names)}: {table_name}")

                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                indexes = inspector.get_indexes(table_name)

                tables.append({
                    "name": table_name,
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                            "default": col.get("default"),
                        }
                        for col in columns
                    ],
                    "primary_keys": pk_constraint.get("constrained_columns", []),
                    "foreign_keys": [
                        {
                            "name": fk.get("name"),
                            "columns": fk.get("constrained_columns", []),
                            "referred_table": fk.get("referred_table"),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                        for fk in foreign_keys
                    ],
                    "indexes": [
                        {
                            "name": idx_info.get("name"),
                            "columns": idx_info.get("column_names", []),
                            "unique": idx_info.get("unique", False),
                        }
                        for idx_info in indexes
                    ],
                })
            except Exception as e:
                logger.warning(f"Error extracting schema for table '{table_name}': {e}")
                # Continue with other tables
                continue

        logger.info(f"Successfully extracted schema for {len(tables)} tables from '{name}'")

        return {
            "connection_name": name,
            "tables": tables,
            "table_count": len(tables),
        }

    finally:
        # Dispose the engine after use
        engine.dispose()


@router.get("/connections/{name}/schema", response_model=Dict[str, Any])
async def get_database_schema(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract database schema"""
    try:
        # 验证用户是否拥有该连接
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found"
            )

        # Run schema extraction in thread pool to avoid blocking
        connection_key = f"{current_user.id}:{name}"
        loop = asyncio.get_event_loop()
        schema_result = await loop.run_in_executor(None, _extract_schema_sync, connection_key)

        return schema_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract schema: {str(e)}",
        )


@router.get("/ontologies", response_model=List[Dict[str, Any]])
async def list_ontologies():
    """
    List all stored ontologies from all database connections.

    Returns:
        List of ontology metadata including connection name, version, statistics, etc.
    """
    try:
        # Get ontology storage path from config
        ontology_path = Path("./ontology_store")
        if not ontology_path.exists():
            return []

        ontologies = []

        def process_ontology_dir(conn_dir: Path):
            """Process a connection directory and extract ontology metadata."""
            # Look for ontology file (v3 first, then v2)
            v3_file = conn_dir / "ontology_v3.json"
            v2_file = conn_dir / "ontology_v2.json"
            ontology_file = v3_file if v3_file.exists() else v2_file
            if not ontology_file.exists():
                return None

            try:
                with open(ontology_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    version = data.get("version", "2.0")

                    # V3 格式：schema.classes.{domain}.{class_name}
                    # V2 格式：classes 是列表
                    if version.startswith("3"):
                        schema_classes = data.get("schema", {}).get("classes", {})
                        class_count = sum(len(domain_classes) for domain_classes in schema_classes.values())
                        # V3 中 attributes 在每个 class 的 attributes 字段
                        property_count = sum(
                            len(cls.get("attributes", {}))
                            for domain_classes in schema_classes.values()
                            for cls in domain_classes.values()
                        )
                    else:
                        classes = data.get("classes", [])
                        class_count = len(classes)
                        property_count = sum(len(cls.get("properties", [])) for cls in classes)

                    # 从 meta 获取创建时间
                    meta = data.get("meta", {})
                    created_at = meta.get("created_at") or data.get("created_at")

                    return {
                        "connection_name": meta.get("source_connection") or data.get("connection_name", conn_dir.name),
                        "version": version,
                        "created_at": created_at,
                        "concept_count": class_count,
                        "property_count": property_count,
                        "relationship_count": len(data.get("relationships", [])),
                        "business_rule_count": len(data.get("business_rules", [])),
                        "uncertainty_count": len(data.get("uncertainties", [])),
                        "has_domain_insights": bool(data.get("domains") or meta.get("domains")),
                    }
            except Exception as e:
                logger.warning(f"Error reading ontology file {ontology_file}: {e}")
                return None

        # 遍历 ontology_store 目录
        # 支持两种结构:
        # 1. ontology_store/{connection_name}/ (旧结构)
        # 2. ontology_store/{user_id}/{connection_name}/ (多租户结构)
        for item in ontology_path.iterdir():
            if not item.is_dir():
                continue

            # 检查是否是连接目录（包含 ontology 文件）
            if (item / "ontology_v3.json").exists() or (item / "ontology_v2.json").exists():
                # 旧结构: ontology_store/{connection_name}/
                result = process_ontology_dir(item)
                if result:
                    ontologies.append(result)
            else:
                # 可能是用户 ID 目录，检查子目录
                for sub_item in item.iterdir():
                    if sub_item.is_dir():
                        result = process_ontology_dir(sub_item)
                        if result:
                            ontologies.append(result)

        return ontologies

    except Exception as e:
        logger.error(f"Error listing ontologies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ontologies: {str(e)}",
        )


def _find_ontology_path(name: str) -> Path | None:
    """
    Find ontology directory by connection name.
    Supports both old structure (ontology_store/{name}) and
    multi-tenant structure (ontology_store/{user_id}/{name}).
    """
    ontology_store = Path("./ontology_store")
    if not ontology_store.exists():
        return None

    # 先检查旧结构: ontology_store/{name}/
    direct_path = ontology_store / name
    if direct_path.exists() and direct_path.is_dir():
        if (direct_path / "ontology_v3.json").exists() or (direct_path / "ontology_v2.json").exists():
            return direct_path

    # 检查多租户结构: ontology_store/{user_id}/{name}/
    for user_dir in ontology_store.iterdir():
        if not user_dir.is_dir():
            continue
        conn_path = user_dir / name
        if conn_path.exists() and conn_path.is_dir():
            if (conn_path / "ontology_v3.json").exists() or (conn_path / "ontology_v2.json").exists():
                return conn_path

    return None


@router.get("/ontologies/{name}", response_model=Dict[str, Any])
async def get_ontology(name: str, version: str = "latest"):
    """
    Get a specific ontology for a database connection.

    Args:
        name: Database connection name
        version: Ontology version (default: "latest")

    Returns:
        Full ontology data including concepts, properties, relationships, etc.
    """
    try:
        # Validate connection name
        if not name or name in ["undefined", "null", ""]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid connection name. Please select a valid ontology.",
            )

        ontology_path = _find_ontology_path(name)
        if not ontology_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ontology for connection '{name}' not found. Please build ontology first.",
            )

        # 优先使用 v3，回退到 v2
        if version == "latest":
            v3_path = ontology_path / "ontology_v3.json"
            v2_path = ontology_path / "ontology_v2.json"
            file_path = v3_path if v3_path.exists() else v2_path
        elif version == "v3":
            file_path = ontology_path / "ontology_v3.json"
        elif version == "v2":
            file_path = ontology_path / "ontology_v2.json"
        else:
            file_path = ontology_path / f"ontology_{version}.json"

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ontology for connection '{name}' (version '{version}') not found. Please build ontology first.",
            )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ontology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ontology: {str(e)}",
        )


@router.post("/ontologies/{name}/search", response_model=List[Dict[str, Any]])
async def search_ontology(name: str, search_query: OntologySearchQuery):
    """Search within an ontology"""
    try:
        # Get ontology
        ontology_path = Path("./ontology_store")
        file_path = ontology_path / f"{name}.json"

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ontology '{name}' not found",
            )

        with open(file_path, "r", encoding="utf-8") as f:
            ontology = json.load(f)

        # Simple text search (can be enhanced with semantic search later)
        results = []
        query_lower = search_query.query.lower()

        for entity in ontology.get("entities", []):
            score = 0.0
            matched_field = None

            # Check entity name
            if query_lower in entity.get("name", "").lower():
                score += 1.0
                matched_field = "name"

            # Check description
            if entity.get("description") and query_lower in entity["description"].lower():
                score += 0.5
                if not matched_field:
                    matched_field = "description"

            # Filter by entity type if specified
            if search_query.entity_types:
                if entity.get("type") not in search_query.entity_types:
                    continue

            if score > 0:
                results.append({
                    "entity": entity,
                    "score": score,
                    "matched_field": matched_field or "unknown",
                })

        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[: search_query.limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching ontology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search ontology: {str(e)}",
        )


@router.post("/ontologies/{name}/export")
async def export_ontology(name: str, export_request: OntologyExportRequest):
    """
    Export ontology in specified format with selective content.

    Supports:
    - JSON: Full structured export
    - CSV: Tabular format (concepts and relationships in separate sections)
    - Markdown: Human-readable documentation format

    Args:
        name: Database connection name
        export_request: Export options (format, content selection, domain filter)

    Returns:
        File download response in requested format
    """
    try:
        # Validate connection name
        if not name or name in ["undefined", "null", ""]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid connection name",
            )

        # Load ontology using shared finder
        ontology_path = _find_ontology_path(name)
        if not ontology_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ontology for connection '{name}' not found",
            )

        v3_path = ontology_path / "ontology_v3.json"
        v2_path = ontology_path / "ontology_v2.json"
        file_path = v3_path if v3_path.exists() else v2_path

        with open(file_path, "r", encoding="utf-8") as f:
            ontology_data = json.load(f)

        # Filter data based on export options
        export_data = _filter_ontology_for_export(
            ontology_data,
            export_request.include_concepts,
            export_request.include_relationships,
            export_request.include_business_rules,
            export_request.include_uncertainties,
            export_request.selected_domains,
        )

        # Generate export content based on format
        export_format = export_request.format.lower()

        if export_format == "json":
            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            media_type = "application/json"
            filename = f"{name}_ontology.json"

        elif export_format == "csv":
            content = _convert_ontology_to_csv(export_data)
            media_type = "text/csv"
            filename = f"{name}_ontology.csv"

        elif export_format == "markdown":
            content = _convert_ontology_to_markdown(export_data, name)
            media_type = "text/markdown"
            filename = f"{name}_ontology.md"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {export_format}. Use json, csv, or markdown.",
            )

        return Response(
            content=content.encode("utf-8"),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": f"{media_type}; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting ontology: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export ontology: {str(e)}",
        )


def _filter_ontology_for_export(
    ontology_data: Dict[str, Any],
    include_concepts: bool,
    include_relationships: bool,
    include_business_rules: bool,
    include_uncertainties: bool,
    selected_domains: List[str] = None,
) -> Dict[str, Any]:
    """Filter ontology data based on export options."""
    result = {
        "meta": ontology_data.get("meta", {}),
        "version": ontology_data.get("version", "2.0"),
    }

    version = ontology_data.get("version", "2.0")

    if include_concepts:
        if version.startswith("3"):
            # V3 format: schema.classes.{domain}.{class}
            schema_classes = ontology_data.get("schema", {}).get("classes", {})
            if selected_domains:
                filtered_classes = {
                    domain: classes
                    for domain, classes in schema_classes.items()
                    if domain in selected_domains
                }
            else:
                filtered_classes = schema_classes
            result["concepts"] = filtered_classes
        else:
            # V2 format: classes list
            classes = ontology_data.get("classes", [])
            if selected_domains:
                filtered_classes = [
                    c for c in classes
                    if c.get("domain") in selected_domains
                ]
            else:
                filtered_classes = classes
            result["concepts"] = filtered_classes

    if include_relationships:
        relationships = ontology_data.get("relationships", [])
        if selected_domains:
            # Filter relationships by source/target domain
            filtered_rels = []
            for rel in relationships:
                source_domain = rel.get("source_domain", "")
                target_domain = rel.get("target_domain", "")
                if source_domain in selected_domains or target_domain in selected_domains:
                    filtered_rels.append(rel)
            result["relationships"] = filtered_rels
        else:
            result["relationships"] = relationships

    if include_business_rules:
        result["business_rules"] = ontology_data.get("business_rules", [])

    if include_uncertainties:
        result["uncertainties"] = ontology_data.get("uncertainties", [])

    return result


def _convert_ontology_to_csv(export_data: Dict[str, Any]) -> str:
    """Convert ontology data to CSV format."""
    output = io.StringIO()

    # Concepts section
    concepts = export_data.get("concepts", {})
    if concepts:
        output.write("=== 概念/实体 ===\n")
        writer = csv.writer(output)
        writer.writerow(["领域", "技术名称", "业务名称", "描述", "数据来源", "重要性"])

        if isinstance(concepts, dict):
            # V3 format
            for domain, classes in concepts.items():
                for class_name, class_data in classes.items():
                    writer.writerow([
                        domain,
                        class_data.get("technical_name", class_name),
                        class_data.get("business_name_cn", ""),
                        class_data.get("description", ""),
                        class_data.get("data_source", ""),
                        class_data.get("importance", ""),
                    ])
        else:
            # V2 format (list)
            for cls in concepts:
                writer.writerow([
                    cls.get("domain", ""),
                    cls.get("technical_name", cls.get("name", "")),
                    cls.get("business_name_cn", ""),
                    cls.get("description", ""),
                    cls.get("data_source", ""),
                    cls.get("importance", ""),
                ])

    # Relationships section
    relationships = export_data.get("relationships", [])
    if relationships:
        output.write("\n=== 关系 ===\n")
        writer = csv.writer(output)
        writer.writerow(["源概念", "关系类型", "目标概念", "强度", "描述"])
        for rel in relationships:
            writer.writerow([
                rel.get("source_concept", ""),
                rel.get("relationship_type", ""),
                rel.get("target_concept", ""),
                rel.get("strength", ""),
                rel.get("description", ""),
            ])

    # Business rules section
    business_rules = export_data.get("business_rules", [])
    if business_rules:
        output.write("\n=== 业务规则 ===\n")
        writer = csv.writer(output)
        writer.writerow(["规则名称", "描述", "相关实体"])
        for rule in business_rules:
            writer.writerow([
                rule.get("name", ""),
                rule.get("description", ""),
                ", ".join(rule.get("related_entities", [])),
            ])

    return output.getvalue()


def _convert_ontology_to_markdown(export_data: Dict[str, Any], connection_name: str) -> str:
    """Convert ontology data to Markdown format."""
    lines = []
    meta = export_data.get("meta", {})

    # Header
    lines.append(f"# {connection_name} 业务本体")
    lines.append("")
    lines.append(f"**版本**: {export_data.get('version', '2.0')}")
    if meta.get("created_at"):
        lines.append(f"**创建时间**: {meta.get('created_at')}")
    lines.append("")

    # Concepts section
    concepts = export_data.get("concepts", {})
    if concepts:
        lines.append("## 概念/实体")
        lines.append("")

        if isinstance(concepts, dict):
            # V3 format: grouped by domain
            for domain, classes in concepts.items():
                lines.append(f"### {domain}")
                lines.append("")
                lines.append("| 技术名称 | 业务名称 | 描述 | 数据来源 |")
                lines.append("|---------|---------|------|---------|")
                for class_name, class_data in classes.items():
                    tech_name = class_data.get("technical_name", class_name)
                    biz_name = class_data.get("business_name_cn", "")
                    desc = class_data.get("description", "").replace("\n", " ")[:100]
                    source = class_data.get("data_source", "")
                    lines.append(f"| {tech_name} | {biz_name} | {desc} | {source} |")
                lines.append("")
        else:
            # V2 format
            lines.append("| 技术名称 | 业务名称 | 描述 | 领域 |")
            lines.append("|---------|---------|------|------|")
            for cls in concepts:
                tech_name = cls.get("technical_name", cls.get("name", ""))
                biz_name = cls.get("business_name_cn", "")
                desc = cls.get("description", "").replace("\n", " ")[:100]
                domain = cls.get("domain", "")
                lines.append(f"| {tech_name} | {biz_name} | {desc} | {domain} |")
            lines.append("")

    # Relationships section
    relationships = export_data.get("relationships", [])
    if relationships:
        lines.append("## 关系")
        lines.append("")
        lines.append("| 源概念 | 关系类型 | 目标概念 | 强度 |")
        lines.append("|-------|---------|---------|------|")
        for rel in relationships:
            source = rel.get("source_concept", "")
            rel_type = rel.get("relationship_type", "")
            target = rel.get("target_concept", "")
            strength = rel.get("strength", "")
            lines.append(f"| {source} | {rel_type} | {target} | {strength} |")
        lines.append("")

    # Business rules section
    business_rules = export_data.get("business_rules", [])
    if business_rules:
        lines.append("## 业务规则")
        lines.append("")
        for rule in business_rules:
            lines.append(f"### {rule.get('name', '规则')}")
            lines.append("")
            lines.append(rule.get("description", ""))
            if rule.get("related_entities"):
                lines.append("")
                lines.append(f"**相关实体**: {', '.join(rule.get('related_entities', []))}")
            lines.append("")

    # Uncertainties section
    uncertainties = export_data.get("uncertainties", [])
    if uncertainties:
        lines.append("## 待确认问题")
        lines.append("")
        for unc in uncertainties:
            priority = unc.get("priority", "medium")
            priority_badge = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            lines.append(f"- {priority_badge} **{unc.get('entity', '')}**: {unc.get('question', '')}")
        lines.append("")

    return "\n".join(lines)


@router.post("/connections/{name}/query", response_model=Dict[str, Any])
async def execute_query(
    name: str,
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute SQL query on a database connection"""
    try:
        # 验证用户是否拥有该连接
        result = await db.execute(
            select(DatabaseConnectionModel).where(
                DatabaseConnectionModel.user_id == current_user.id,
                DatabaseConnectionModel.name == name
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found"
            )

        sql = request_data.get("sql", "")
        params = request_data.get("params")
        fetch_limit = request_data.get("fetch_limit", 100)

        if not sql or not sql.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SQL query is required",
            )

        # Run query in thread pool to avoid blocking
        connection_key = f"{current_user.id}:{name}"
        loop = asyncio.get_event_loop()
        query_result = await loop.run_in_executor(
            None,
            partial(_execute_query_sync, connection_key, sql, params, fetch_limit)
        )

        return query_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute query: {str(e)}",
        )


def _execute_query_sync(
    connection_name: str,
    sql: str,
    params: Dict[str, Any] = None,
    fetch_limit: int = 100
) -> Dict[str, Any]:
    """
    Synchronous query execution function to run in thread pool.
    """
    from sqlalchemy import create_engine, text
    from datetime import datetime
    import re

    connection = db_manager.get_connection(connection_name)
    if not connection:
        raise ValueError(f"Connection '{connection_name}' not found")

    # Create engine
    url = connection.get_connection_url(async_mode=False)
    engine = create_engine(url, pool_pre_ping=True)

    try:
        # Determine query type
        query_type = _get_query_type(sql)
        is_select = query_type == "SELECT"

        with engine.connect() as conn:
            # Execute query
            if params:
                result = conn.execute(text(sql), params)
            else:
                result = conn.execute(text(sql))

            # Process results
            if is_select:
                rows = result.fetchmany(fetch_limit)
                columns = list(result.keys())

                # Convert to list of dicts
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert non-JSON-serializable types
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        elif not isinstance(value, (str, int, float, bool, type(None))):
                            value = str(value)
                        row_dict[col] = value
                    data.append(row_dict)

                has_more = len(rows) == fetch_limit

                return {
                    "status": "success",
                    "query_type": query_type,
                    "row_count": len(data),
                    "has_more": has_more,
                    "columns": columns,
                    "data": data,
                    "message": f"查询返回 {len(data)} 行" +
                              (f" (限制 {fetch_limit} 行，可能有更多)" if has_more else ""),
                }
            else:
                # Write operation
                conn.commit()
                affected_rows = result.rowcount if hasattr(result, 'rowcount') else 0

                return {
                    "status": "success",
                    "query_type": query_type,
                    "affected_rows": affected_rows,
                    "message": f"{query_type} 操作完成，影响 {affected_rows} 行",
                }

    except Exception as e:
        error_msg = str(e)
        return {
            "status": "error",
            "message": f"查询执行失败: {error_msg}",
            "query_type": _get_query_type(sql),
        }
    finally:
        engine.dispose()


def _get_query_type(sql: str) -> str:
    """Determine SQL query type"""
    import re
    sql_clean = sql.strip()
    sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
    sql_clean = re.sub(r'--.*?(\n|$)', '', sql_clean)
    sql_clean = sql_clean.strip()

    match = re.match(r'^\s*(\w+)', sql_clean, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"
