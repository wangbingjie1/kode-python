"""
Ontology Async Tasks

本体相关的异步任务（Celery）。
如果 Celery 不可用，会同步执行任务。
"""

from typing import Optional, List, Dict, Any
import asyncio
from kode.services.celery_app import celery_app, CELERY_AVAILABLE
from kode.services.vector_index_manager import VectorIndexManager
from kode.services.ontology_version_manager import OntologyVersionManager
from kode.database.session import async_session_maker
from kode.models.ontology_version import OntologyVersion
from kode.utils.logger import get_logger
from sqlalchemy import select

logger = get_logger(__name__)


def _build_vector_index_impl(version_id: str, force_rebuild: bool = False):
    """
    构建向量索引任务实现（同步版本）

    Args:
        version_id: 本体版本ID
        force_rebuild: 是否强制重建

    Returns:
        任务结果字典
    """
    try:
        # 运行异步逻辑
        result = asyncio.run(_build_vector_index_async(version_id, force_rebuild, None))
        return result

    except Exception as e:
        logger.error(f"向量索引构建任务失败: version_id={version_id}, error={e}", exc_info=True)
        return {
            "success": False,
            "version_id": version_id,
            "error": str(e)
        }


# 根据 Celery 可用性决定使用哪个版本
if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="kode.build_vector_index")
    def build_vector_index_task(self, version_id: str, force_rebuild: bool = False):
        """Celery 异步任务版本"""
        try:
            self.update_state(state="PROGRESS", meta={"status": "初始化向量索引构建任务"})
            result = asyncio.run(_build_vector_index_async(version_id, force_rebuild, self))
            return result
        except Exception as e:
            logger.error(f"向量索引构建任务失败: {e}", exc_info=True)
            return {"success": False, "version_id": version_id, "error": str(e)}
else:
    # 降级到同步执行
    def build_vector_index_task(version_id: str, force_rebuild: bool = False):
        """同步执行版本（Celery 不可用时）"""
        logger.info(f"同步执行向量索引构建: version_id={version_id}")
        return _build_vector_index_impl(version_id, force_rebuild)

    # 添加 delay 方法以保持 API 兼容
    build_vector_index_task.delay = lambda *args, **kwargs: type('MockTask', (), {
        'id': 'sync-execution',
        '__dict__': _build_vector_index_impl(*args, **kwargs)
    })()


async def _build_vector_index_async(version_id: str, force_rebuild: bool, task=None):
    """
    异步构建向量索引的内部逻辑

    Args:
        version_id: 本体版本ID
        force_rebuild: 是否强制重建
        task: Celery 任务对象（可选，用于更新状态）

    Returns:
        任务结果字典
    """
    async with async_session_maker() as session:
        try:
            # 更新任务状态（如果有）
            if task:
                task.update_state(state="PROGRESS", meta={"status": "查询本体版本"})

            # 查询版本
            version_manager = OntologyVersionManager()
            stmt = select(OntologyVersion).where(OntologyVersion.id == version_id)
            result = await session.execute(stmt)
            version = result.scalar_one_or_none()

            if not version:
                raise ValueError(f"版本不存在: version_id={version_id}")

            # 加载本体数据
            if task:
                task.update_state(state="PROGRESS", meta={"status": "加载本体数据"})
            ontology_data = await version_manager.load_ontology_data(session, version)

            if not ontology_data:
                raise ValueError(f"无法加载本体数据: version_id={version_id}")

            # 构建向量索引
            if task:
                task.update_state(state="PROGRESS", meta={"status": "构建向量索引"})
            vector_manager = VectorIndexManager()
            success = await vector_manager.build_index_for_version(
                session=session,
                ontology_version=version,
                ontology_data=ontology_data,
                force_rebuild=force_rebuild
            )

            if success:
                logger.info(f"向量索引构建成功: version_id={version_id}")
                return {
                    "success": True,
                    "version_id": version_id,
                    "user_id": version.user_id,
                    "connection_name": version.connection_name,
                    "version_number": version.version_number
                }
            else:
                raise RuntimeError("向量索引构建失败")

        except Exception as e:
            logger.error(f"向量索引构建异常: {e}", exc_info=True)
            raise


def _rebuild_vector_index_impl(version_id: str, changed_entities: Optional[List[str]] = None):
    """
    重建向量索引任务实现（同步版本）

    Args:
        version_id: 本体版本ID
        changed_entities: 变更的实体列表

    Returns:
        任务结果字典
    """
    try:
        result = asyncio.run(_rebuild_vector_index_async(version_id, changed_entities, None))
        return result

    except Exception as e:
        logger.error(f"向量索引重建任务失败: version_id={version_id}, error={e}", exc_info=True)
        return {
            "success": False,
            "version_id": version_id,
            "error": str(e)
        }


# 根据 Celery 可用性决定使用哪个版本
if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, name="kode.rebuild_vector_index_on_change")
    def rebuild_vector_index_on_change_task(self, version_id: str, changed_entities: Optional[List[str]] = None):
        """Celery 异步任务版本"""
        try:
            self.update_state(state="PROGRESS", meta={"status": "初始化向量索引重建任务"})
            result = asyncio.run(_rebuild_vector_index_async(version_id, changed_entities, self))
            return result
        except Exception as e:
            logger.error(f"向量索引重建任务失败: {e}", exc_info=True)
            return {"success": False, "version_id": version_id, "error": str(e)}
else:
    # 降级到同步执行
    def rebuild_vector_index_on_change_task(version_id: str, changed_entities: Optional[List[str]] = None):
        """同步执行版本（Celery 不可用时）"""
        logger.info(f"同步执行向量索引重建: version_id={version_id}")
        return _rebuild_vector_index_impl(version_id, changed_entities)

    rebuild_vector_index_on_change_task.delay = lambda *args, **kwargs: type('MockTask', (), {
        'id': 'sync-execution',
        '__dict__': _rebuild_vector_index_impl(*args, **kwargs)
    })()


async def _rebuild_vector_index_async(version_id: str, changed_entities: Optional[List[str]], task=None):
    """
    异步重建向量索引的内部逻辑

    Args:
        version_id: 本体版本ID
        changed_entities: 变更的实体列表
        task: Celery 任务对象（可选）

    Returns:
        任务结果字典
    """
    async with async_session_maker() as session:
        try:
            if task:
                task.update_state(state="PROGRESS", meta={"status": "查询本体版本"})

            # 查询版本
            version_manager = OntologyVersionManager()
            stmt = select(OntologyVersion).where(OntologyVersion.id == version_id)
            result = await session.execute(stmt)
            version = result.scalar_one_or_none()

            if not version:
                raise ValueError(f"版本不存在: version_id={version_id}")

            # 加载本体数据
            if task:
                task.update_state(state="PROGRESS", meta={"status": "加载本体数据"})
            ontology_data = await version_manager.load_ontology_data(session, version)

            if not ontology_data:
                raise ValueError(f"无法加载本体数据: version_id={version_id}")

            # 重建向量索引
            if task:
                task.update_state(state="PROGRESS", meta={"status": "重建向量索引"})
            vector_manager = VectorIndexManager()
            success = await vector_manager.rebuild_index_on_change(
                session=session,
                ontology_version=version,
                ontology_data=ontology_data,
                changed_entities=changed_entities
            )

            if success:
                logger.info(
                    f"向量索引重建成功: version_id={version_id}, "
                    f"changed_entities={changed_entities}"
                )
                return {
                    "success": True,
                    "version_id": version_id,
                    "changed_entities": changed_entities
                }
            else:
                raise RuntimeError("向量索引重建失败")

        except Exception as e:
            logger.error(f"向量索引重建异常: {e}", exc_info=True)
            raise
