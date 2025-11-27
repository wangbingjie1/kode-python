"""
新版本本体文件存储管理

负责管理业务上下文和新格式本体的文件持久化
"""

from pathlib import Path
import json
from typing import Optional, Dict, Any
from datetime import datetime


class OntologyStorageV2:
    """新版本本体文件存储管理器

    存储结构：
    ontology_store/
        {connection_name}/
            business_context.json  # 业务理解五问答案
            ontology_v2.json       # 新格式本体
            schema.json            # 原有schema（保留）
            ontology.json          # 旧格式本体（保留，向后兼容）
    """

    def __init__(self, base_path: str = "ontology_store"):
        self.base_path = Path(base_path)

    def _ensure_connection_dir(self, connection_name: str) -> Path:
        """确保连接目录存在"""
        conn_dir = self.base_path / connection_name
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
        path = self.base_path / connection_name / "business_context.json"
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_business_context(
        self,
        connection_name: str,
        new_answers: Dict[str, str]
    ) -> Path:
        """更新业务理解答案（增量更新）

        Args:
            connection_name: 数据库连接名
            new_answers: 新的答案（会合并到已有答案）

        Returns:
            保存的文件路径
        """
        existing = self.load_business_context(connection_name)

        if existing:
            # 合并答案
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
        """保存新格式本体

        Args:
            connection_name: 数据库连接名
            ontology_data: 本体数据（包含meta/domains/classes等）

        Returns:
            保存的文件路径
        """
        path = self._ensure_connection_dir(connection_name) / "ontology_v2.json"

        # 自动注入元数据
        ontology_data["version"] = "2.0"
        ontology_data["updated_at"] = datetime.now().isoformat()

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(ontology_data, f, ensure_ascii=False, indent=2)

        return path

    def load_ontology_v2(
        self,
        connection_name: str
    ) -> Optional[Dict[str, Any]]:
        """加载新格式本体

        Args:
            connection_name: 数据库连接名

        Returns:
            本体数据，不存在时返回None
        """
        path = self.base_path / connection_name / "ontology_v2.json"
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def ontology_v2_exists(self, connection_name: str) -> bool:
        """检查新格式本体是否存在

        Args:
            connection_name: 数据库连接名

        Returns:
            是否存在
        """
        path = self.base_path / connection_name / "ontology_v2.json"
        return path.exists()

    # ============ 旧格式兼容 ============

    def load_ontology_v1(
        self,
        connection_name: str
    ) -> Optional[Dict[str, Any]]:
        """加载旧格式本体（向后兼容）

        Args:
            connection_name: 数据库连接名

        Returns:
            旧格式本体数据，不存在时返回None
        """
        path = self.base_path / connection_name / "ontology.json"
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ============ 工具方法 ============

    def list_connections(self) -> list[str]:
        """列出所有已有的连接名

        Returns:
            连接名列表
        """
        if not self.base_path.exists():
            return []

        return [
            d.name for d in self.base_path.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

    def get_connection_info(self, connection_name: str) -> Dict[str, Any]:
        """获取连接的元信息

        Args:
            connection_name: 数据库连接名

        Returns:
            包含各类文件存在状态的字典
        """
        conn_dir = self.base_path / connection_name
        if not conn_dir.exists():
            return {
                "exists": False,
                "connection_name": connection_name
            }

        return {
            "exists": True,
            "connection_name": connection_name,
            "has_business_context": (conn_dir / "business_context.json").exists(),
            "has_ontology_v2": (conn_dir / "ontology_v2.json").exists(),
            "has_ontology_v1": (conn_dir / "ontology.json").exists(),
            "has_schema": (conn_dir / "schema.json").exists(),
            "business_context_completed": self.is_business_context_completed(connection_name)
        }
