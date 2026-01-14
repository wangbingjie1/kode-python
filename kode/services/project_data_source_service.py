"""
ProjectDataSource Service - 项目数据源关联业务逻辑
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from kode.models.data_source import DataSource
from kode.models.project import Project
from kode.models.project_data_source import ProjectDataSource, ProjectDataSourceStatus
from kode.models.project_ontology import ProjectOntology

logger = logging.getLogger(__name__)


class ProjectDataSourceService:
    """项目数据源关联服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_data_source(
        self,
        project_id: str,
        data_source_id: str,
        organization_id: str,
    ) -> Tuple[bool, str, Optional[ProjectDataSource]]:
        """
        关联数据源到项目

        Returns:
            (success, message, association)
        """
        # 验证项目属于该组织
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            return False, "项目不存在或不属于当前组织", None

        # 验证数据源属于该组织
        result = await self.db.execute(
            select(DataSource).where(
                DataSource.id == data_source_id,
                DataSource.organization_id == organization_id,
            )
        )
        ds = result.scalar_one_or_none()
        if not ds:
            return False, "数据源不存在或不属于当前组织", None

        # 检查是否已关联
        result = await self.db.execute(
            select(ProjectDataSource).where(
                ProjectDataSource.project_id == project_id,
                ProjectDataSource.data_source_id == data_source_id,
            )
        )
        if result.scalar_one_or_none():
            return False, "数据源已关联到该项目", None

        # 创建关联
        assoc = ProjectDataSource(
            id=str(uuid4()),
            project_id=project_id,
            data_source_id=data_source_id,
            status=ProjectDataSourceStatus.LINKED,
        )
        self.db.add(assoc)
        await self.db.commit()
        await self.db.refresh(assoc)

        logger.info(f"Data source {data_source_id} linked to project {project_id}")
        return True, "关联成功", assoc

    async def unlink_data_source(
        self,
        project_id: str,
        data_source_id: str,
        organization_id: str,
    ) -> Tuple[bool, str]:
        """
        解绑数据源（已融合的需要先剥离）
        """
        # 验证项目属于该组织
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        if not result.scalar_one_or_none():
            return False, "项目不存在或不属于当前组织"

        # 查找关联
        result = await self.db.execute(
            select(ProjectDataSource).where(
                ProjectDataSource.project_id == project_id,
                ProjectDataSource.data_source_id == data_source_id,
            )
        )
        assoc = result.scalar_one_or_none()

        if not assoc:
            return False, "数据源未关联到该项目"

        # 检查是否已融合
        if assoc.status == ProjectDataSourceStatus.MERGED:
            return False, "数据源已融合到本体，请先执行剥离操作"

        await self.db.delete(assoc)
        await self.db.commit()

        logger.info(f"Data source {data_source_id} unlinked from project {project_id}")
        return True, "解绑成功"

    async def merge_to_ontology(
        self,
        project_id: str,
        data_source_id: str,
        organization_id: str,
        conversation_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        将数据源融合到项目本体
        """
        # 验证项目属于该组织
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        if not result.scalar_one_or_none():
            return False, "项目不存在或不属于当前组织"

        # 查找关联
        result = await self.db.execute(
            select(ProjectDataSource).where(
                ProjectDataSource.project_id == project_id,
                ProjectDataSource.data_source_id == data_source_id,
            )
        )
        assoc = result.scalar_one_or_none()

        if not assoc:
            return False, "数据源未关联到该项目"

        if assoc.status == ProjectDataSourceStatus.MERGED:
            return False, "数据源已融合"

        # 更新状态
        assoc.status = ProjectDataSourceStatus.MERGED
        assoc.merged_at = datetime.utcnow()
        assoc.merged_by_conversation_id = conversation_id

        # 更新项目本体的融合列表
        result = await self.db.execute(
            select(ProjectOntology).where(ProjectOntology.project_id == project_id)
        )
        ontology = result.scalar_one_or_none()

        if ontology:
            merged_ids = ontology.merged_data_source_ids or []
            if data_source_id not in merged_ids:
                merged_ids.append(data_source_id)
                ontology.merged_data_source_ids = merged_ids

        await self.db.commit()

        logger.info(
            f"Data source {data_source_id} merged to project {project_id} ontology"
        )
        return True, "融合成功"

    async def unmerge_from_ontology(
        self,
        project_id: str,
        data_source_id: str,
        organization_id: str,
    ) -> Tuple[bool, str]:
        """
        从项目本体中剥离数据源
        """
        # 验证项目属于该组织
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        if not result.scalar_one_or_none():
            return False, "项目不存在或不属于当前组织"

        # 查找关联
        result = await self.db.execute(
            select(ProjectDataSource).where(
                ProjectDataSource.project_id == project_id,
                ProjectDataSource.data_source_id == data_source_id,
            )
        )
        assoc = result.scalar_one_or_none()

        if not assoc:
            return False, "数据源未关联到该项目"

        if assoc.status != ProjectDataSourceStatus.MERGED:
            return False, "数据源未融合，无需剥离"

        # 更新状态
        assoc.status = ProjectDataSourceStatus.LINKED
        assoc.merged_at = None
        assoc.merged_by_conversation_id = None

        # 从本体融合列表移除
        result = await self.db.execute(
            select(ProjectOntology).where(ProjectOntology.project_id == project_id)
        )
        ontology = result.scalar_one_or_none()

        if ontology and ontology.merged_data_source_ids:
            merged_ids = list(ontology.merged_data_source_ids)
            if data_source_id in merged_ids:
                merged_ids.remove(data_source_id)
                ontology.merged_data_source_ids = merged_ids

        await self.db.commit()

        # TODO: 实际从本体数据中移除该数据源的 schema

        logger.info(
            f"Data source {data_source_id} unmerged from project {project_id} ontology"
        )
        return True, "剥离成功"

    async def get_project_data_sources(
        self,
        project_id: str,
        organization_id: str,
    ) -> List[dict]:
        """
        获取项目关联的所有数据源
        """
        # 验证项目属于该组织
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.organization_id == organization_id,
            )
        )
        if not result.scalar_one_or_none():
            return []

        result = await self.db.execute(
            select(ProjectDataSource)
            .options(selectinload(ProjectDataSource.data_source))
            .where(ProjectDataSource.project_id == project_id)
        )
        associations = result.scalars().all()

        return [
            {
                "id": a.id,
                "data_source_id": a.data_source_id,
                "data_source_name": a.data_source.name if a.data_source else None,
                "data_source_type": (
                    a.data_source.source_type.value if a.data_source else None
                ),
                "status": a.status.value,
                "merged_at": a.merged_at.isoformat() if a.merged_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in associations
        ]

    async def link_multiple_data_sources(
        self,
        project_id: str,
        data_source_ids: List[str],
        organization_id: str,
    ) -> Tuple[int, int, List[str]]:
        """
        批量关联数据源到项目

        Returns:
            (success_count, fail_count, error_messages)
        """
        success_count = 0
        fail_count = 0
        errors = []

        for ds_id in data_source_ids:
            success, message, _ = await self.link_data_source(
                project_id=project_id,
                data_source_id=ds_id,
                organization_id=organization_id,
            )
            if success:
                success_count += 1
            else:
                fail_count += 1
                errors.append(f"{ds_id}: {message}")

        return success_count, fail_count, errors
