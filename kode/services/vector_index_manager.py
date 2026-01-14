"""
Vector Index Manager

管理本体版本的向量索引构建、重建和状态追踪。
使用 ChromaDB 作为向量数据库。
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from kode.models.ontology_version import OntologyVersion
from kode.utils.logger import get_logger

logger = get_logger(__name__)


class VectorIndexManager:
    """向量索引管理器"""

    def __init__(self, base_path: str = "ontology_store"):
        self.base_path = Path(base_path)

    def _get_vector_index_path(self, user_id: str, connection_name: str, version_number: int) -> Path:
        """获取向量索引目录路径"""
        return self.base_path / user_id / connection_name / "vectors" / f"v{version_number}" / ".chroma"

    async def build_index_for_version(
        self,
        session: AsyncSession,
        ontology_version: OntologyVersion,
        ontology_data: Dict[str, Any],
        force_rebuild: bool = False
    ) -> bool:
        """
        为指定版本构建向量索引

        Args:
            session: 数据库会话
            ontology_version: 本体版本对象
            ontology_data: 本体数据
            force_rebuild: 是否强制重建（忽略已有索引）

        Returns:
            是否构建成功
        """
        try:
            # 检查状态
            if ontology_version.vector_index_status == "ready" and not force_rebuild:
                logger.info(f"版本 v{ontology_version.version_number} 的向量索引已就绪，跳过构建")
                return True

            # 更新状态为 building
            ontology_version.vector_index_status = "building"
            ontology_version.vector_index_error = None
            session.add(ontology_version)
            await session.commit()

            # 获取向量索引路径
            vector_path = self._get_vector_index_path(
                ontology_version.user_id,
                ontology_version.connection_name,
                ontology_version.version_number
            )
            vector_path.parent.mkdir(parents=True, exist_ok=True)

            # 执行向量化（调用 ChromaDB）
            success = await self._build_chroma_index(vector_path, ontology_data, ontology_version.version_number)

            if success:
                # 更新状态为 ready
                ontology_version.vector_index_status = "ready"
                ontology_version.vector_index_built_at = datetime.now()
                ontology_version.vector_index_error = None
                logger.info(
                    f"向量索引构建成功: user={ontology_version.user_id}, "
                    f"conn={ontology_version.connection_name}, v{ontology_version.version_number}"
                )
            else:
                # 更新状态为 failed
                ontology_version.vector_index_status = "failed"
                ontology_version.vector_index_error = "向量索引构建失败（未知错误）"
                logger.error(
                    f"向量索引构建失败: user={ontology_version.user_id}, "
                    f"conn={ontology_version.connection_name}, v{ontology_version.version_number}"
                )

            session.add(ontology_version)
            await session.commit()

            return success

        except Exception as e:
            logger.error(f"向量索引构建异常: {e}", exc_info=True)

            # 更新状态为 failed
            ontology_version.vector_index_status = "failed"
            ontology_version.vector_index_error = str(e)
            session.add(ontology_version)
            await session.commit()

            return False

    async def _build_chroma_index(
        self,
        vector_path: Path,
        ontology_data: Dict[str, Any],
        index_version: int
    ) -> bool:
        """
        使用 ChromaDB 构建向量索引

        Args:
            vector_path: ChromaDB 持久化目录
            ontology_data: 本体数据
            index_version: 索引版本号

        Returns:
            是否构建成功
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.error("ChromaDB 未安装，无法构建向量索引")
            return False

        try:
            # 初始化 ChromaDB 客户端
            client = chromadb.PersistentClient(
                path=str(vector_path),
                settings=Settings(anonymized_telemetry=False)
            )

            # 创建集合（如果已存在则删除重建）
            try:
                client.delete_collection(name="ontology_concepts")
                client.delete_collection(name="ontology_properties")
            except Exception:
                pass  # 集合不存在时忽略错误

            concepts_collection = client.create_collection(
                name="ontology_concepts",
                metadata={"hnsw:space": "cosine", "index_version": str(index_version)}
            )

            properties_collection = client.create_collection(
                name="ontology_properties",
                metadata={"hnsw:space": "cosine", "index_version": str(index_version)}
            )

            # 索引本体数据（复用 OntologySearchTool 的逻辑）
            self._index_ontology_to_chroma(
                ontology_data,
                concepts_collection,
                properties_collection,
                index_version
            )

            logger.info(f"ChromaDB 向量索引构建完成: {vector_path}")
            return True

        except Exception as e:
            logger.error(f"ChromaDB 索引构建失败: {e}", exc_info=True)
            return False

    def _index_ontology_to_chroma(
        self,
        ontology: Dict[str, Any],
        concepts_collection,
        properties_collection,
        index_version: int
    ):
        """
        将本体数据索引到 ChromaDB 集合

        支持 V1 (concepts/properties)、V2 (classes 数组) 和 V3 (schema.classes 对象) 三种格式。
        （复用自 OntologySearchTool._index_ontology）
        """
        concept_ids = []
        concept_docs = []
        concept_metadatas = []
        property_ids = []
        property_docs = []
        property_metadatas = []

        # 检测格式并获取 classes
        classes = []
        if "schema" in ontology and "classes" in ontology["schema"]:
            # V3 格式：{"schema": {"classes": {"User": {...}, "Order": {...}}}}
            classes_dict = ontology["schema"]["classes"]
            classes = [
                {"key": key, **value}
                for key, value in classes_dict.items()
            ]
        elif "classes" in ontology and isinstance(ontology["classes"], list):
            # V2 格式：{"classes": [{"key": "User", ...}, {"key": "Order", ...}]}
            classes = ontology["classes"]
        elif "concepts" in ontology:
            # V1 格式：{"concepts": [...]}（兼容旧版）
            classes = ontology["concepts"]

        # 索引 classes/concepts
        for cls in classes:
            key = cls.get("key", cls.get("name", ""))
            if not key:
                continue

            # 构建文档文本（用于向量化）
            doc_parts = [
                cls.get("business_name", ""),
                cls.get("description", ""),
                cls.get("technical_name", ""),
                ", ".join(cls.get("table_names", [])),
            ]
            doc = " | ".join([p for p in doc_parts if p])

            concept_ids.append(f"class:{key}")
            concept_docs.append(doc)
            concept_metadatas.append({
                "type": "class",
                "key": key,
                "business_name": cls.get("business_name", ""),
                "technical_name": cls.get("technical_name", ""),
            })

            # 索引 properties
            properties = cls.get("properties", [])
            for prop in properties:
                prop_key = prop.get("key", "")
                if not prop_key:
                    continue

                # 构建文档文本
                prop_doc_parts = [
                    prop.get("business_name", ""),
                    prop.get("description", ""),
                    prop.get("technical_name", ""),
                    prop.get("data_type", ""),
                ]
                prop_doc = " | ".join([p for p in prop_doc_parts if p])

                property_ids.append(f"property:{key}.{prop_key}")
                property_docs.append(prop_doc)
                property_metadatas.append({
                    "type": "property",
                    "class_key": key,
                    "key": prop_key,
                    "business_name": prop.get("business_name", ""),
                    "technical_name": prop.get("technical_name", ""),
                })

        # 批量插入到 ChromaDB
        if concept_ids:
            concepts_collection.add(
                ids=concept_ids,
                documents=concept_docs,
                metadatas=concept_metadatas
            )

        if property_ids:
            properties_collection.add(
                ids=property_ids,
                documents=property_docs,
                metadatas=property_metadatas
            )

        logger.info(
            f"索引完成: {len(concept_ids)} 个类, {len(property_ids)} 个属性, 版本 v{index_version}"
        )

    async def rebuild_index_on_change(
        self,
        session: AsyncSession,
        ontology_version: OntologyVersion,
        ontology_data: Dict[str, Any],
        changed_entities: Optional[List[str]] = None
    ) -> bool:
        """
        本体变更后重建向量索引

        Args:
            session: 数据库会话
            ontology_version: 本体版本对象
            ontology_data: 本体数据
            changed_entities: 变更的实体列表（可选，用于增量更新）

        Returns:
            是否重建成功
        """
        # 如果指定了 changed_entities，可以实现增量更新
        # 当前简化实现：全量重建
        logger.info(
            f"重建向量索引: user={ontology_version.user_id}, "
            f"conn={ontology_version.connection_name}, v{ontology_version.version_number}, "
            f"changed_entities={changed_entities}"
        )

        return await self.build_index_for_version(
            session=session,
            ontology_version=ontology_version,
            ontology_data=ontology_data,
            force_rebuild=True
        )

    async def switch_current_index(
        self,
        session: AsyncSession,
        user_id: str,
        connection_name: str,
        target_version: OntologyVersion
    ):
        """
        切换当前向量索引（用于版本回滚场景）

        通过软链接将 "current" 指向目标版本的向量目录

        Args:
            session: 数据库会话
            user_id: 用户ID
            connection_name: 数据库连接名
            target_version: 目标版本对象
        """
        vector_base = self.base_path / user_id / connection_name / "vectors"
        current_link = vector_base / "current"
        target_dir = f"v{target_version.version_number}"

        # 删除旧的软链接（如果存在）
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()

        # 创建新的软链接
        try:
            current_link.symlink_to(target_dir, target_is_directory=True)
            logger.info(
                f"切换向量索引: user={user_id}, conn={connection_name}, "
                f"current -> v{target_version.version_number}"
            )
        except Exception as e:
            logger.error(f"创建软链接失败: {e}", exc_info=True)
            raise

    async def check_index_status(
        self,
        session: AsyncSession,
        ontology_version: OntologyVersion
    ) -> str:
        """
        检查向量索引状态

        Args:
            session: 数据库会话
            ontology_version: 本体版本对象

        Returns:
            状态字符串：pending/building/ready/failed
        """
        return ontology_version.vector_index_status
