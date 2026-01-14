"""DataSource Service - 数据源业务逻辑"""

import os
import time
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from kode.models.data_source import DataSource, DataSourceType, DataSourceStatus
from kode.models.project_data_source import ProjectDataSource
from kode.core.security import encrypt_db_password, decrypt_db_password
from kode.services.database_manager import DatabaseConnection, db_manager

logger = logging.getLogger(__name__)


class DataSourceService:
    """数据源服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_file_data_source(
        self,
        organization_id: str,
        name: str,
        file_path: str,
        original_filename: str,
        file_size: int,
        file_mime_type: Optional[str] = None,
    ) -> DataSource:
        """创建文件类型数据源"""
        ds = DataSource(
            id=str(uuid4()),
            organization_id=organization_id,
            name=name,
            source_type=DataSourceType.FILE,
            status=DataSourceStatus.READY,
            file_path=file_path,
            original_filename=original_filename,
            file_size=file_size,
            file_mime_type=file_mime_type,
        )
        self.db.add(ds)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def create_database_data_source(
        self,
        organization_id: str,
        name: str,
        source_type: DataSourceType,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        db_schema: Optional[str] = None,
        ssl_enabled: bool = False,
        config: Optional[dict] = None,
    ) -> DataSource:
        """创建数据库类型数据源"""
        # 加密密码
        encrypted_pwd = encrypt_db_password(password)

        ds = DataSource(
            id=str(uuid4()),
            organization_id=organization_id,
            name=name,
            source_type=source_type,
            status=DataSourceStatus.PENDING,
            host=host,
            port=port,
            database=database,
            username=username,
            encrypted_password=encrypted_pwd,
            db_schema=db_schema,
            ssl_enabled=ssl_enabled,
            config=config,
        )
        self.db.add(ds)
        await self.db.commit()
        await self.db.refresh(ds)
        return ds

    async def get_by_id(
        self, data_source_id: str, organization_id: str
    ) -> Optional[DataSource]:
        """根据ID获取数据源"""
        result = await self.db.execute(
            select(DataSource).where(
                DataSource.id == data_source_id,
                DataSource.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self, name: str, organization_id: str
    ) -> Optional[DataSource]:
        """根据名称获取数据源"""
        result = await self.db.execute(
            select(DataSource).where(
                DataSource.name == name,
                DataSource.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: str,
        source_type: Optional[DataSourceType] = None,
        status: Optional[DataSourceStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[DataSource], int]:
        """列出组织的所有数据源"""
        query = select(DataSource).where(
            DataSource.organization_id == organization_id
        )

        if source_type:
            query = query.where(DataSource.source_type == source_type)
        if status:
            query = query.where(DataSource.status == status)

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页
        query = query.offset(skip).limit(limit).order_by(DataSource.created_at.desc())
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def delete(
        self, data_source_id: str, organization_id: str
    ) -> Tuple[bool, str]:
        """删除数据源（检查引用）"""
        ds = await self.get_by_id(data_source_id, organization_id)
        if not ds:
            return False, "数据源不存在"

        # 检查是否被项目引用
        result = await self.db.execute(
            select(ProjectDataSource).where(
                ProjectDataSource.data_source_id == data_source_id
            )
        )
        associations = result.scalars().all()

        if associations:
            # 获取项目数量
            project_count = len(associations)
            return False, f"数据源被 {project_count} 个项目引用，无法删除"

        # 如果是文件类型，删除物理文件
        if ds.source_type == DataSourceType.FILE and ds.file_path:
            try:
                if os.path.exists(ds.file_path):
                    os.remove(ds.file_path)
                    logger.info(f"已删除文件: {ds.file_path}")
            except Exception as e:
                logger.warning(f"删除文件失败: {e}")

        await self.db.delete(ds)
        await self.db.commit()
        return True, "删除成功"

    async def test_connection(
        self, data_source_id: str, organization_id: str
    ) -> Tuple[bool, str, Optional[float]]:
        """测试数据库连接"""
        ds = await self.get_by_id(data_source_id, organization_id)
        if not ds:
            return False, "数据源不存在", None

        if ds.source_type == DataSourceType.FILE:
            return False, "文件类型无需测试连接", None

        try:
            # 解密密码
            password = (
                decrypt_db_password(ds.encrypted_password)
                if ds.encrypted_password
                else ""
            )

            # 使用全局 db_manager 测试连接
            start = time.time()

            # 创建临时连接配置
            temp_name = f"_test_{ds.id}"
            connection = DatabaseConnection(
                name=temp_name,
                db_type=ds.source_type.value,
                host=ds.host,
                port=ds.port,
                database=ds.database,
                username=ds.username,
                password=password,
                db_schema=ds.db_schema,
                ssl=ds.ssl_enabled,
            )

            # 添加临时连接
            db_manager._connections[temp_name] = connection

            try:
                # 测试连接
                result = db_manager.test_connection(temp_name)
                latency = (time.time() - start) * 1000

                if result["status"] == "success":
                    ds.status = DataSourceStatus.READY
                    ds.error_message = None
                    await self.db.commit()
                    return True, "连接成功", latency
                else:
                    ds.status = DataSourceStatus.ERROR
                    ds.error_message = result.get("error", result.get("message"))
                    await self.db.commit()
                    return False, result.get("message", "连接失败"), latency

            finally:
                # 清理临时连接
                db_manager.close_connection(temp_name)
                db_manager.remove_connection(temp_name)

        except Exception as e:
            ds.status = DataSourceStatus.ERROR
            ds.error_message = str(e)
            await self.db.commit()
            logger.exception(f"测试连接失败: {e}")
            return False, str(e), None

    async def test_connection_params(
        self,
        source_type: DataSourceType,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        db_schema: Optional[str] = None,
        ssl_enabled: bool = False,
    ) -> Tuple[bool, str, Optional[float]]:
        """测试连接参数（创建前测试）"""
        try:
            start = time.time()

            # 创建临时连接配置
            temp_name = f"_test_{uuid4().hex[:8]}"
            connection = DatabaseConnection(
                name=temp_name,
                db_type=source_type.value,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                db_schema=db_schema,
                ssl=ssl_enabled,
            )

            # 添加临时连接
            db_manager._connections[temp_name] = connection

            try:
                # 测试连接
                result = db_manager.test_connection(temp_name)
                latency = (time.time() - start) * 1000

                if result["status"] == "success":
                    return True, "连接成功", latency
                else:
                    return False, result.get("message", "连接失败"), latency

            finally:
                # 清理临时连接
                db_manager.close_connection(temp_name)
                db_manager.remove_connection(temp_name)

        except Exception as e:
            logger.exception(f"测试连接失败: {e}")
            return False, str(e), None

    async def update_status(
        self,
        data_source_id: str,
        status: DataSourceStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """更新数据源状态"""
        ds = await self.db.get(DataSource, data_source_id)
        if ds:
            ds.status = status
            ds.error_message = error_message
            await self.db.commit()
