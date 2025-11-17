"""
Database Management API Routes

REST endpoints for database connection management, schema extraction,
and ontology operations.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from pathlib import Path
import json
import asyncio
from functools import partial

from kode.schemas.database import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
    DatabaseConnectionResponse,
    DatabaseTestResult,
    DatabaseSchemaResponse,
    OntologyResponse,
    OntologySearchQuery,
    OntologySearchResult,
)
from kode.services.database_manager import (
    DatabaseConnection,
    DatabaseConnectionManager,
    db_manager,
)
from kode.database.session import SessionLocal
from kode.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.post(
    "/connections",
    response_model=DatabaseConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(connection_data: DatabaseConnectionCreate):
    """Create a new database connection"""
    db_session = SessionLocal()
    try:
        # Create connection object
        connection = DatabaseConnection(
            name=connection_data.name,
            db_type=connection_data.db_type,
            host=connection_data.host,
            port=connection_data.port,
            database=connection_data.database,
            username=connection_data.username,
            password=connection_data.password,
            db_schema=connection_data.db_schema,
            ssl=connection_data.ssl,
        )

        # Add to manager
        db_manager.add_connection(connection)

        # Persist to database
        db_manager.save_connection_to_db(db_session, connection)

        logger.info(f"Created and persisted database connection: {connection_data.name}")
        return DatabaseConnectionResponse(**connection.to_dict())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}",
        )
    finally:
        db_session.close()


@router.get("/connections", response_model=List[DatabaseConnectionResponse])
async def list_connections():
    """List all database connections"""
    try:
        connection_names = db_manager.list_connections()
        connections = []

        for name in connection_names:
            conn = db_manager.get_connection(name)
            if conn:
                connections.append(DatabaseConnectionResponse(**conn.to_dict()))

        return connections

    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}",
        )


@router.get("/connections/{name}", response_model=DatabaseConnectionResponse)
async def get_connection(name: str):
    """Get a specific database connection"""
    try:
        connection = db_manager.get_connection(name)

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
async def update_connection(name: str, update_data: DatabaseConnectionUpdate):
    """Update a database connection"""
    db_session = SessionLocal()
    try:
        # Get existing connection
        existing = db_manager.get_connection(name)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        # Close existing engines (async version)
        await db_manager.close_connection_async(name)

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        # Persist changes to database
        db_manager.save_connection_to_db(db_session, existing)

        logger.info(f"Updated database connection: {name}")
        return DatabaseConnectionResponse(**existing.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update connection: {str(e)}",
        )
    finally:
        db_session.close()


@router.delete("/connections/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(name: str):
    """Delete a database connection"""
    db_session = SessionLocal()
    try:
        # Check if connection exists
        connection = db_manager.get_connection(name)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        # Close engines first (async version)
        await db_manager.close_connection_async(name)

        # Remove from in-memory manager
        db_manager.remove_connection(name)

        # Remove from database persistence
        db_manager.delete_connection_from_db(db_session, name)

        logger.info(f"Deleted database connection: {name}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}",
        )
    finally:
        db_session.close()


@router.post("/connections/{name}/test", response_model=DatabaseTestResult)
async def test_connection(name: str):
    """Test a database connection"""
    try:
        # Test connection
        result = await db_manager.test_connection_async(name)

        if result["status"] == "error":
            return DatabaseTestResult(
                status="error",
                message=result["message"],
                error=result.get("error"),
            )

        return DatabaseTestResult(
            status="success",
            message=result["message"],
            connection=DatabaseConnectionResponse(**result["connection"]),
        )

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
async def get_database_schema(name: str):
    """Extract database schema"""
    try:
        # Get connection
        connection = db_manager.get_connection(name)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
            )

        # Run schema extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _extract_schema_sync, name)

        return result

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
        # Each connection has its own directory
        for conn_dir in ontology_path.iterdir():
            if not conn_dir.is_dir():
                continue

            # Look for ontology_latest.json
            latest_file = conn_dir / "ontology_latest.json"
            if latest_file.exists():
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        ontology = data.get("ontology", {})
                        ontologies.append({
                            "connection_name": data.get("connection_name"),
                            "version": data.get("version"),
                            "created_at": data.get("created_at"),
                            "concept_count": len(ontology.get("concepts", {})),
                            "property_count": len(ontology.get("properties", {})),
                            "relationship_count": len(ontology.get("relationships", [])),
                            "uncertainty_count": len(ontology.get("uncertainties", [])),
                            "has_domain_insights": "domain_insights" in ontology,
                        })
                except Exception as e:
                    logger.warning(f"Error reading ontology file {latest_file}: {e}")
                    continue

        return ontologies

    except Exception as e:
        logger.error(f"Error listing ontologies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ontologies: {str(e)}",
        )


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

        ontology_path = Path("./ontology_store") / name

        if version == "latest":
            file_path = ontology_path / "ontology_latest.json"
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


@router.post("/connections/{name}/query", response_model=Dict[str, Any])
async def execute_query(name: str, request_data: Dict[str, Any]):
    """Execute SQL query on a database connection"""
    try:
        # Get connection
        connection = db_manager.get_connection(name)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{name}' not found",
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
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(_execute_query_sync, name, sql, params, fetch_limit)
        )

        return result

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
