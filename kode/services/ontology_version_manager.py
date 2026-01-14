"""
Ontology Version Manager

管理本体版本的 CRUD 操作，包括版本创建、查询、回滚等功能。
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from kode.models.ontology_version import OntologyVersion
from kode.models.ontology_change import OntologyChange
from kode.utils.logger import get_logger

logger = get_logger(__name__)


class OntologyVersionManager:
    """本体版本管理器"""

    def __init__(self, base_path: str = "ontology_store"):
        self.base_path = Path(base_path)

    def _calculate_hash(self, ontology_data: Dict[str, Any]) -> str:
        """计算本体数据的 SHA256 哈希值"""
        content = json.dumps(ontology_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _ensure_version_dir(self, user_id: str, connection_name: str, version_number: int) -> Path:
        """确保版本目录存在"""
        version_dir = self.base_path / user_id / connection_name / "versions" / f"v{version_number}"
        version_dir.mkdir(parents=True, exist_ok=True)
        return version_dir

    def _ensure_vector_dir(self, user_id: str, connection_name: str, version_number: int) -> Path:
        """确保向量索引目录存在"""
        vector_dir = self.base_path / user_id / connection_name / "vectors" / f"v{version_number}"
        vector_dir.mkdir(parents=True, exist_ok=True)
        return vector_dir

    async def get_latest_version(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str
    ) -> Optional[OntologyVersion]:
        """获取指定连接的最新版本"""
        stmt = select(OntologyVersion).where(
            and_(
                OntologyVersion.user_id == user_id,
                OntologyVersion.connection_name == connection_name,
                OntologyVersion.status == "active"
            )
        ).order_by(desc(OntologyVersion.version_number)).limit(1)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version_by_number(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        version_number: int
    ) -> Optional[OntologyVersion]:
        """根据版本号获取版本"""
        stmt = select(OntologyVersion).where(
            and_(
                OntologyVersion.user_id == user_id,
                OntologyVersion.connection_name == connection_name,
                OntologyVersion.version_number == version_number
            )
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[OntologyVersion]:
        """列出用户的所有版本（分页）"""
        stmt = select(OntologyVersion).where(
            and_(
                OntologyVersion.user_id == user_id,
                OntologyVersion.connection_name == connection_name,
                OntologyVersion.status == "active"
            )
        ).order_by(desc(OntologyVersion.version_number)).limit(limit).offset(offset)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_version(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        ontology_data: Dict[str, Any],
        change_summary: Optional[str] = None,
        conversation_id: Optional[str] = None,
        version_tag: Optional[str] = None,
        is_snapshot: bool = False
    ) -> OntologyVersion:
        """
        创建新版本

        Args:
            session: 数据库会话
            user_id: 用户ID
            connection_name: 数据库连接名
            ontology_data: 本体数据
            change_summary: 变更摘要
            conversation_id: 对话ID
            version_tag: 版本标签（可选）
            is_snapshot: 是否为快照

        Returns:
            新创建的版本对象
        """
        # 计算哈希值
        ontology_hash = self._calculate_hash(ontology_data)

        # 检查是否存在相同内容的版本（去重）
        stmt = select(OntologyVersion).where(
            and_(
                OntologyVersion.user_id == user_id,
                OntologyVersion.connection_name == connection_name,
                OntologyVersion.ontology_hash == ontology_hash,
                OntologyVersion.status == "active"
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"本体内容未变化，复用已有版本 v{existing.version_number}")
            return existing

        # 获取最新版本号
        latest_version = await self.get_latest_version(session, user_id, connection_name)
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # 将当前版本的 is_current 设置为 False
        if latest_version:
            latest_version.is_current = False
            session.add(latest_version)

        # 确定存储策略
        size_bytes = len(json.dumps(ontology_data, ensure_ascii=False).encode('utf-8'))
        storage_type = "db" if size_bytes < 100 * 1024 else "file"  # 小于100KB存数据库

        # 创建版本目录
        version_dir = self._ensure_version_dir(user_id, connection_name, new_version_number)
        vector_dir = self._ensure_vector_dir(user_id, connection_name, new_version_number)

        # 保存文件
        file_path = None
        ontology_data_for_db = None

        if storage_type == "file":
            file_path = f"ontology_v{new_version_number}.json"
            full_path = version_dir / file_path
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(ontology_data, f, ensure_ascii=False, indent=2)
            logger.info(f"本体文件已保存到: {full_path}")
        else:
            ontology_data_for_db = ontology_data

        # 创建数据库记录
        new_version = OntologyVersion(
            id=str(uuid.uuid4()),
            user_id=user_id,
            connection_name=connection_name,
            version_number=new_version_number,
            version_tag=version_tag,
            is_snapshot=is_snapshot,
            parent_version_id=latest_version.id if latest_version else None,
            storage_type=storage_type,
            file_path=file_path,
            ontology_data=ontology_data_for_db,
            ontology_hash=ontology_hash,
            vector_index_status="pending",  # 初始状态为待构建
            vector_index_path=str(vector_dir.relative_to(self.base_path)),
            size_bytes=size_bytes,
            change_summary=change_summary,
            created_by_conversation_id=conversation_id,
            status="active",
            is_current=True
        )

        session.add(new_version)
        await session.commit()
        await session.refresh(new_version)

        logger.info(
            f"创建新版本: user={user_id}, conn={connection_name}, "
            f"v{new_version_number}, hash={ontology_hash[:8]}..."
        )

        return new_version

    async def load_ontology_data(
        self,
        session: AsyncSession,
        version: OntologyVersion
    ) -> Optional[Dict[str, Any]]:
        """加载版本的本体数据"""
        if version.storage_type == "db":
            return version.ontology_data

        # 从文件加载
        if not version.file_path:
            logger.error(f"版本 {version.id} 的 file_path 为空")
            return None

        full_path = self.base_path / version.user_id / version.connection_name / "versions" / f"v{version.version_number}" / version.file_path

        if not full_path.exists():
            logger.error(f"本体文件不存在: {full_path}")
            return None

        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def rollback_to_version(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        target_version_number: int,
        conversation_id: Optional[str] = None
    ) -> OntologyVersion:
        """
        回滚到指定版本

        实际上是将目标版本的内容作为新版本创建（不删除历史版本）

        Args:
            session: 数据库会话
            user_id: 用户ID
            connection_name: 数据库连接名
            target_version_number: 目标版本号
            conversation_id: 对话ID

        Returns:
            新创建的版本（内容与目标版本相同）
        """
        # 获取目标版本
        target_version = await self.get_version_by_number(
            session, user_id, connection_name, target_version_number
        )

        if not target_version:
            raise ValueError(f"版本 v{target_version_number} 不存在")

        # 加载目标版本的数据
        ontology_data = await self.load_ontology_data(session, target_version)

        if not ontology_data:
            raise ValueError(f"无法加载版本 v{target_version_number} 的数据")

        # 创建新版本（内容与目标版本相同）
        new_version = await self.create_version(
            session=session,
            user_id=user_id,
            connection_name=connection_name,
            ontology_data=ontology_data,
            change_summary=f"回滚到版本 v{target_version_number}",
            conversation_id=conversation_id,
            is_snapshot=False
        )

        logger.info(
            f"回滚成功: user={user_id}, conn={connection_name}, "
            f"从 v{target_version_number} 创建新版本 v{new_version.version_number}"
        )

        return new_version

    async def delete_version(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        version_number: int
    ) -> bool:
        """
        软删除版本（标记为 deleted，不真删数据）

        Args:
            session: 数据库会话
            user_id: 用户ID
            connection_name: 数据库连接名
            version_number: 版本号

        Returns:
            是否删除成功
        """
        version = await self.get_version_by_number(
            session, user_id, connection_name, version_number
        )

        if not version:
            return False

        # 不允许删除当前活跃版本
        if version.is_current:
            raise ValueError("不能删除当前活跃版本，请先切换到其他版本")

        version.status = "deleted"
        session.add(version)
        await session.commit()

        logger.info(f"软删除版本: user={user_id}, conn={connection_name}, v{version_number}")
        return True

    async def get_version_count(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str
    ) -> int:
        """获取版本总数"""
        stmt = select(func.count(OntologyVersion.id)).where(
            and_(
                OntologyVersion.user_id == user_id,
                OntologyVersion.connection_name == connection_name,
                OntologyVersion.status == "active"
            )
        )

        result = await session.execute(stmt)
        return result.scalar_one()
