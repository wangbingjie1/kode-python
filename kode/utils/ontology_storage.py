"""
新版本本体文件存储管理

负责管理业务上下文和新格式本体的文件持久化
支持用户隔离和版本管理（通过 contextvars 自动获取 user_id）
"""

from pathlib import Path
import json
from typing import Optional, Dict, Any
from datetime import datetime
from kode.utils.context import get_current_user_id


class OntologyStorageV2:
    """新版本本体文件存储管理器

    存储结构（已更新为用户隔离）：
    ontology_store/
        {user_id}/
            {connection_name}/
                versions/
                    v1/, v2/, v3/...       # 版本化本体文件
                vectors/
                    v1/, v2/, v3/...       # 版本化向量索引
                    current -> v3/          # 软链接指向当前版本
                business_context.json      # 业务理解五问答案（兼容旧版）
    """

    def __init__(self, base_path: str = "ontology_store"):
        """初始化本体存储管理器

        Args:
            base_path: 存储根目录

        Note:
            user_id 通过 contextvars 自动获取，无需手动设置
        """
        self.base_path = Path(base_path)

    def _get_user_id(self) -> str:
        """从 contextvars 获取当前用户ID

        Returns:
            用户ID（开发环境降级到 'default'）
        """
        return get_current_user_id()

    def _get_ontology_file_path(self, connection_name: str, for_write: bool = False) -> Path:
        """获取本体文件路径（内部方法，兼容旧版逻辑）

        注意：新版本应使用 OntologyVersionManager，此方法仅用于向后兼容

        Args:
            connection_name: 数据库连接名
            for_write: 是否用于写入（写入时总是使用最新版本 v3）

        Returns:
            本体文件路径
        """
        conn_dir = self.base_path / self._get_user_id() / connection_name

        if for_write:
            # 写入时总是使用 v3
            return conn_dir / "ontology_v3.json"

        # 读取时优先使用 v3，回退到 v2
        v3_path = conn_dir / "ontology_v3.json"
        if v3_path.exists():
            return v3_path

        return conn_dir / "ontology_v2.json"

    def _ensure_connection_dir(self, connection_name: str) -> Path:
        """确保连接目录存在"""
        conn_dir = self.base_path / self._get_user_id() / connection_name
        conn_dir.mkdir(parents=True, exist_ok=True)
        return conn_dir

    # ============ 业务上下文管理 ============

    def save_business_context(
        self,
        connection_name: str,
        answers: Dict[str, str],
        conversation_id: Optional[int] = None
    ) -> Path:
        """保存业务理解答案

        Args:
            connection_name: 数据库连接名
            answers: 业务理解五问答案字典
            conversation_id: 可选的对话ID

        Returns:
            保存的文件路径
        """
        path = self._ensure_connection_dir(connection_name) / "business_context.json"

        data = {
            "conversation_id": conversation_id,
            "answers": answers,
            "completed": len(answers) >= 5,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return path

    def load_business_context(
        self,
        connection_name: str
    ) -> Optional[Dict[str, Any]]:
        """加载业务理解答案

        Args:
            connection_name: 数据库连接名

        Returns:
            业务上下文数据，不存在时返回None
        """
        path = self.base_path / self._get_user_id() / connection_name / "business_context.json"
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_business_context(
        self,
        connection_name: str,
        new_answers: Dict[str, str]
    ) -> Path:
        """更新业务理解答案（增量更新，保留其他字段）

        Args:
            connection_name: 数据库连接名
            new_answers: 新的答案（会合并到已有答案）

        Returns:
            保存的文件路径
        """
        existing = self.load_business_context(connection_name)

        if existing:
            # 合并答案，保留其他字段（如 qa_text, qa_pairs）
            if "answers" not in existing:
                existing["answers"] = {}
            existing["answers"].update(new_answers)
            existing["completed"] = len(existing["answers"]) >= 5
            existing["updated_at"] = datetime.now().isoformat()
            data = existing
        else:
            # 首次创建
            data = {
                "conversation_id": None,
                "answers": new_answers,
                "completed": len(new_answers) >= 5,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        path = self._ensure_connection_dir(connection_name) / "business_context.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return path

    def is_business_context_completed(self, connection_name: str) -> bool:
        """检查业务理解是否完成（五问都已回答）

        Args:
            connection_name: 数据库连接名

        Returns:
            是否完成
        """
        context = self.load_business_context(connection_name)
        if not context:
            return False
        return context.get("completed", False)

    # ============ 新格式本体管理 ============

    def save_ontology_v2(
        self,
        connection_name: str,
        ontology_data: Dict[str, Any]
    ) -> Path:
        """保存本体（自动使用最新版本格式）

        Args:
            connection_name: 数据库连接名
            ontology_data: 本体数据（包含meta/domains/classes等）

        Returns:
            保存的文件路径
        """
        self._ensure_connection_dir(connection_name)
        path = self._get_ontology_file_path(connection_name, for_write=True)

        # 自动注入元数据（保留原始 version 如果已存在）
        if "version" not in ontology_data:
            ontology_data["version"] = "3.0"
        ontology_data["updated_at"] = datetime.now().isoformat()

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(ontology_data, f, ensure_ascii=False, indent=2)

        return path

    def load_ontology_v2(
        self,
        connection_name: str
    ) -> Optional[Dict[str, Any]]:
        """加载本体（优先 v3，回退到 v2）

        Args:
            connection_name: 数据库连接名

        Returns:
            本体数据，不存在时返回None
        """
        path = self._get_ontology_file_path(connection_name, for_write=False)
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def ontology_v2_exists(self, connection_name: str) -> bool:
        """检查本体是否存在（v3 或 v2）

        Args:
            connection_name: 数据库连接名

        Returns:
            是否存在
        """
        conn_dir = self.base_path / self._get_user_id() / connection_name
        v3_path = conn_dir / "ontology_v3.json"
        v2_path = conn_dir / "ontology_v2.json"
        return v3_path.exists() or v2_path.exists()

    # ============ 工具方法 ============

    def list_connections(self) -> list[str]:
        """列出当前用户的所有连接名

        Returns:
            连接名列表
        """
        user_dir = self.base_path / self._get_user_id()
        if not user_dir.exists():
            return []

        return [
            d.name for d in user_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

    def get_connection_info(self, connection_name: str) -> Dict[str, Any]:
        """获取当前用户连接的元信息

        Args:
            connection_name: 数据库连接名

        Returns:
            包含各类文件存在状态的字典
        """
        user_id = self._get_user_id()
        conn_dir = self.base_path / user_id / connection_name
        if not conn_dir.exists():
            return {
                "exists": False,
                "user_id": user_id,
                "connection_name": connection_name
            }

        return {
            "exists": True,
            "user_id": user_id,
            "connection_name": connection_name,
            "has_business_context": (conn_dir / "business_context.json").exists(),
            "has_ontology_v2": self.ontology_v2_exists(connection_name),  # 检查 v3 或 v2
            "has_schema": (conn_dir / "schema.json").exists(),
            "business_context_completed": self.is_business_context_completed(connection_name)
        }
