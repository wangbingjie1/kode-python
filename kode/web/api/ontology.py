"""
Ontology API Routes

本体版本管理的 REST API 端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, field_serializer
from datetime import datetime

from kode.database.session import get_db
from kode.models.user import User
from kode.models.ontology_version import OntologyVersion
from kode.services.ontology_version_manager import OntologyVersionManager
from kode.services.vector_index_manager import VectorIndexManager
from kode.services.ontology_tasks import build_vector_index_task, rebuild_vector_index_on_change_task
from kode.web.dependencies import get_current_user
from kode.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ontology", tags=["ontology"])


# ============ Pydantic Schemas ============

class OntologyVersionResponse(BaseModel):
    """本体版本响应模型"""
    id: str
    user_id: str
    connection_name: str
    version_number: int
    version_tag: Optional[str]
    is_snapshot: bool
    parent_version_id: Optional[str]
    storage_type: str
    file_path: Optional[str]
    ontology_hash: str
    vector_index_status: str
    vector_index_path: Optional[str]
    vector_index_built_at: Optional[datetime]
    vector_index_error: Optional[str]
    size_bytes: Optional[int]
    change_summary: Optional[str]
    created_by_conversation_id: Optional[str]
    status: str
    is_current: bool
    created_at: datetime
    archived_at: Optional[datetime]

    class Config:
        from_attributes = True

    @field_serializer('created_at', 'archived_at', 'vector_index_built_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """将 datetime 序列化为 ISO 格式字符串"""
        if dt is None:
            return None
        return dt.isoformat()


class VersionListResponse(BaseModel):
    """版本列表响应"""
    total: int
    versions: List[OntologyVersionResponse]


class RollbackRequest(BaseModel):
    """回滚请求"""
    target_version_number: int
    conversation_id: Optional[str] = None


class RebuildIndexRequest(BaseModel):
    """重建索引请求"""
    force_rebuild: bool = True


# ============ API Endpoints ============

@router.get("/versions/{connection_name}", response_model=VersionListResponse)
async def list_ontology_versions(
    connection_name: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    列出指定连接的所有本体版本

    Args:
        connection_name: 数据库连接名
        limit: 每页数量
        offset: 偏移量
        current_user: 当前用户
        session: 数据库会话

    Returns:
        版本列表
    """
    try:
        version_manager = OntologyVersionManager()

        # 获取版本列表
        versions = await version_manager.list_versions(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            limit=limit,
            offset=offset
        )

        # 获取总数
        total = await version_manager.get_version_count(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name
        )

        return VersionListResponse(
            total=total,
            versions=[OntologyVersionResponse.model_validate(v) for v in versions]
        )

    except Exception as e:
        logger.error(f"列出版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出版本失败: {str(e)}"
        )


@router.get("/versions/{connection_name}/current", response_model=OntologyVersionResponse)
async def get_current_version(
    connection_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    获取当前活跃版本

    Args:
        connection_name: 数据库连接名
        current_user: 当前用户
        session: 数据库会话

    Returns:
        当前版本
    """
    try:
        version_manager = OntologyVersionManager()

        version = await version_manager.get_latest_version(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到连接 '{connection_name}' 的本体版本"
            )

        return OntologyVersionResponse.model_validate(version)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取当前版本失败: {str(e)}"
        )


@router.get("/versions/{connection_name}/{version_number}", response_model=OntologyVersionResponse)
async def get_version_by_number(
    connection_name: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    根据版本号获取版本

    Args:
        connection_name: 数据库连接名
        version_number: 版本号
        current_user: 当前用户
        session: 数据库会话

    Returns:
        指定版本
    """
    try:
        version_manager = OntologyVersionManager()

        version = await version_manager.get_version_by_number(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            version_number=version_number
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到版本 v{version_number}"
            )

        return OntologyVersionResponse.model_validate(version)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取版本失败: {str(e)}"
        )


@router.post("/versions/{connection_name}/rollback", response_model=OntologyVersionResponse)
async def rollback_to_version(
    connection_name: str,
    request: RollbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    回滚到指定版本

    Args:
        connection_name: 数据库连接名
        request: 回滚请求
        current_user: 当前用户
        session: 数据库会话

    Returns:
        新创建的版本（内容与目标版本相同）
    """
    try:
        version_manager = OntologyVersionManager()

        new_version = await version_manager.rollback_to_version(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            target_version_number=request.target_version_number,
            conversation_id=request.conversation_id
        )

        # 异步触发向量索引重建
        ontology_data = await version_manager.load_ontology_data(session, new_version)
        if ontology_data:
            build_vector_index_task.delay(version_id=new_version.id, force_rebuild=True)
            logger.info(f"已触发向量索引构建任务: version_id={new_version.id}")

        return OntologyVersionResponse.from_orm(new_version)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"回滚版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回滚版本失败: {str(e)}"
        )


@router.post("/versions/{connection_name}/{version_number}/rebuild-index")
async def rebuild_vector_index(
    connection_name: str,
    version_number: int,
    request: RebuildIndexRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    手动触发向量索引重建

    Args:
        connection_name: 数据库连接名
        version_number: 版本号
        request: 重建请求
        current_user: 当前用户
        session: 数据库会话

    Returns:
        任务提交结果
    """
    try:
        version_manager = OntologyVersionManager()

        # 查询版本
        version = await version_manager.get_version_by_number(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            version_number=version_number
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到版本 v{version_number}"
            )

        # 触发异步任务
        task = build_vector_index_task.delay(
            version_id=version.id,
            force_rebuild=request.force_rebuild
        )

        logger.info(
            f"手动触发向量索引重建: user={current_user.id}, "
            f"conn={connection_name}, v{version_number}, task_id={task.id}"
        )

        return {
            "success": True,
            "message": "向量索引重建任务已提交",
            "task_id": task.id,
            "version_id": version.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发向量索引重建失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发向量索引重建失败: {str(e)}"
        )


@router.delete("/versions/{connection_name}/{version_number}")
async def delete_version(
    connection_name: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    删除指定版本（软删除）

    Args:
        connection_name: 数据库连接名
        version_number: 版本号
        current_user: 当前用户
        session: 数据库会话

    Returns:
        删除结果
    """
    try:
        version_manager = OntologyVersionManager()

        success = await version_manager.delete_version(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            version_number=version_number
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到版本 v{version_number}"
            )

        return {
            "success": True,
            "message": f"版本 v{version_number} 已删除"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除版本失败: {str(e)}"
        )


@router.get("/versions/{connection_name}/{version_number}/index-status")
async def get_vector_index_status(
    connection_name: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    查询向量索引状态

    Args:
        connection_name: 数据库连接名
        version_number: 版本号
        current_user: 当前用户
        session: 数据库会话

    Returns:
        索引状态
    """
    try:
        version_manager = OntologyVersionManager()

        version = await version_manager.get_version_by_number(
            session=session,
            user_id=current_user.id,
            connection_name=connection_name,
            version_number=version_number
        )

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到版本 v{version_number}"
            )

        vector_manager = VectorIndexManager()
        status_str = await vector_manager.check_index_status(session, version)

        return {
            "version_id": version.id,
            "version_number": version.version_number,
            "vector_index_status": status_str,
            "vector_index_path": version.vector_index_path,
            "vector_index_built_at": version.vector_index_built_at.isoformat() if version.vector_index_built_at else None,
            "vector_index_error": version.vector_index_error
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询向量索引状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询向量索引状态失败: {str(e)}"
        )
