"""
Ontology Async Tasks

本体相关的异步任务（Celery）。
"""

from typing import Optional, List, Dict, Any
import asyncio
from kode.services.celery_app import celery_app
from kode.services.vector_index_manager import VectorIndexManager
from kode.services.ontology_version_manager import OntologyVersionManager
from kode.database.session import get_async_session
from kode.models.ontology_version import OntologyVersion
from kode.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="kode.build_vector_index")
def build_vector_index_task(
    self,
    version_id: str,
    force_rebuild: bool = False
):
    """
    异步构建向量索引任务

    Args:
        version_id: 本体版本ID
        force_rebuild: 是否强制重建

    Returns:
        任务结果字典
    """
    try:
        # 更新任务状态
        self.update_state(state="PROGRESS", meta={"status": "初始化向量索引构建任务"})

        # 运行异步逻辑
        result = asyncio.run(_build_vector_index_async(version_id, force_rebuild, self))

        return result

    except Exception as e:
        logger.error(f"向量索引构建任务失败: version_id={version_id}, error={e}", exc_info=True)
        return {
            "success": False,
            "version_id": version_id,
            "error": str(e)
        }


async def _build_vector_index_async(version_id: str, force_rebuild: bool, task):
    """
    异步构建向量索引的内部逻辑

    Args:
        version_id: 本体版本ID
        force_rebuild: 是否强制重建
        task: Celery 任务对象（用于更新状态）

    Returns:
        任务结果字典
    """
    async with get_async_session() as session:
        try:
            # 更新任务状态
            task.update_state(state="PROGRESS", meta={"status": "查询本体版本"})

            # 查询版本
            version_manager = OntologyVersionManager()
            stmt = f"SELECT * FROM ontology_versions WHERE id = '{version_id}'"
            result = await session.execute(stmt)
            version = result.scalar_one_or_none()

            if not version:
                raise ValueError(f"版本不存在: version_id={version_id}")

            # 加载本体数据
            task.update_state(state="PROGRESS", meta={"status": "加载本体数据"})
            ontology_data = await version_manager.load_ontology_data(session, version)

            if not ontology_data:
                raise ValueError(f"无法加载本体数据: version_id={version_id}")

            # 构建向量索引
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


@celery_app.task(bind=True, name="kode.rebuild_vector_index_on_change")
def rebuild_vector_index_on_change_task(
    self,
    version_id: str,
    changed_entities: Optional[List[str]] = None
):
    """
    本体变更后重建向量索引任务

    Args:
        version_id: 本体版本ID
        changed_entities: 变更的实体列表（用于增量更新）

    Returns:
        任务结果字典
    """
    try:
        self.update_state(state="PROGRESS", meta={"status": "初始化向量索引重建任务"})

        result = asyncio.run(_rebuild_vector_index_async(version_id, changed_entities, self))

        return result

    except Exception as e:
        logger.error(f"向量索引重建任务失败: version_id={version_id}, error={e}", exc_info=True)
        return {
            "success": False,
            "version_id": version_id,
            "error": str(e)
        }


async def _rebuild_vector_index_async(version_id: str, changed_entities: Optional[List[str]], task):
    """
    异步重建向量索引的内部逻辑

    Args:
        version_id: 本体版本ID
        changed_entities: 变更的实体列表
        task: Celery 任务对象

    Returns:
        任务结果字典
    """
    async with get_async_session() as session:
        try:
            task.update_state(state="PROGRESS", meta={"status": "查询本体版本"})

            # 查询版本
            version_manager = OntologyVersionManager()
            stmt = f"SELECT * FROM ontology_versions WHERE id = '{version_id}'"
            result = await session.execute(stmt)
            version = result.scalar_one_or_none()

            if not version:
                raise ValueError(f"版本不存在: version_id={version_id}")

            # 加载本体数据
            task.update_state(state="PROGRESS", meta={"status": "加载本体数据"})
            ontology_data = await version_manager.load_ontology_data(session, version)

            if not ontology_data:
                raise ValueError(f"无法加载本体数据: version_id={version_id}")

            # 重建向量索引
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
