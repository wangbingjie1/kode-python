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
        """获取本体文件路径（简化版，统一使用 ontology.json）

        Args:
            connection_name: 数据库连接名
            for_write: 是否用于写入

        Returns:
            本体文件路径
        """
        conn_dir = self.base_path / self._get_user_id() / connection_name
        return conn_dir / "ontology.json"

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
        ontology_data: Dict[str, Any],
        change_summary: str = "手动保存"
    ) -> Path:
        """保存本体到 ontology.json，并自动创建版本快照

        ✨ 统一版本管理：
        - 写入前自动创建版本快照到 versions/ 目录
        - 使用临时文件 + 原子替换，防止写入失败损坏数据
        - 自动清理旧版本（保留最近50个）
        - 可选：同步更新数据库版本记录

        Args:
            connection_name: 数据库连接名
            ontology_data: 本体数据（包含meta/domains/classes等）
            change_summary: 变更摘要（用于版本记录）

        Returns:
            保存的文件路径
        """
        import shutil
        import tempfile
        import os

        self._ensure_connection_dir(connection_name)
        path = self._get_ontology_file_path(connection_name, for_write=True)

        # 自动注入元数据
        if "version" not in ontology_data:
            ontology_data["version"] = "3.0"
        ontology_data["updated_at"] = datetime.now().isoformat()

        # ✨ 步骤1：如果主文件存在，先创建版本快照
        version_path = None
        if path.exists():
            version_dir = path.parent / "versions"
            version_dir.mkdir(exist_ok=True)

            # 获取下一个版本号
            next_version = self._get_next_version_number(version_dir)

            # 版本文件名：v{N}_{timestamp}.json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            version_filename = f"v{next_version}_{timestamp}.json"
            version_path = version_dir / version_filename

            # 复制当前主文件到版本快照
            shutil.copy2(path, version_path)
            print(f"📦 已创建版本快照: v{next_version} -> {version_path.name}")

            # ✨ 可选：同步更新数据库版本记录
            self._sync_version_to_database(
                connection_name=connection_name,
                version_number=next_version,
                version_path=version_path,
                change_summary=change_summary
            )

            # ✨ 清理旧版本（保留最近50个）
            self._cleanup_old_versions(version_dir, keep=50)

        # ✨ 步骤2：写入临时文件（防止写入失败损坏主文件）
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".json",
            dir=path.parent,
            text=True
        )
        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(ontology_data, f, ensure_ascii=False, indent=2)

            # ✨ 步骤3：验证临时文件完整性
            with open(temp_path, 'r', encoding='utf-8') as f:
                json.load(f)  # 确保可以解析

            # ✨ 步骤4：原子替换（os.replace 在所有平台都是原子操作）
            os.replace(temp_path, path)

        except Exception as e:
            # 清理临时文件
            if Path(temp_path).exists():
                Path(temp_path).unlink()
            raise e

        return path

    def _get_next_version_number(self, version_dir: Path) -> int:
        """获取下一个版本号

        Args:
            version_dir: 版本目录

        Returns:
            下一个版本号（从1开始）
        """
        if not version_dir.exists():
            return 1

        # 解析所有版本文件名，提取版本号
        version_files = list(version_dir.glob("v*_*.json"))
        if not version_files:
            return 1

        max_version = 0
        for vf in version_files:
            try:
                # 文件名格式：v{N}_{timestamp}.json
                version_str = vf.stem.split('_')[0][1:]  # 去掉 'v' 前缀
                version_num = int(version_str)
                max_version = max(max_version, version_num)
            except (ValueError, IndexError):
                continue

        return max_version + 1

    def _sync_version_to_database(
        self,
        connection_name: str,
        version_number: int,
        version_path: Path,
        change_summary: str
    ):
        """同步版本信息到数据库（可选，不阻塞主流程）

        Args:
            connection_name: 数据库连接名
            version_number: 版本号
            version_path: 版本文件路径
            change_summary: 变更摘要

        Note:
            🔧 修复：移除数据库同步，避免事件循环死锁
            - 版本快照已通过文件系统保存，数据库同步非必需
            - 在后台线程中创建新事件循环会导致死锁
            - 如需数据库版本记录，应在主 API 调用中异步处理
        """
        # ✨ 修复：完全移除数据库同步逻辑，避免事件循环冲突
        # 文件版本快照已足够，数据库同步可以通过定期任务或显式 API 完成
        print(f"📦 版本快照已保存: v{version_number} (数据库同步已禁用，避免死锁)")

    def _cleanup_old_versions(self, version_dir: Path, keep: int = 50) -> None:
        """清理旧版本文件，只保留最近N个

        Args:
            version_dir: 版本目录
            keep: 保留的版本数量（默认50个）
        """
        if not version_dir.exists():
            return

        # 获取所有版本文件（按修改时间排序）
        version_files = sorted(
            version_dir.glob("v*_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # 最新的在前
        )

        # 删除超出保留数量的旧版本
        for old_version in version_files[keep:]:
            try:
                old_version.unlink()
                print(f"🗑️  已删除旧版本: {old_version.name}")
            except Exception as e:
                print(f"删除旧版本失败: {old_version.name}, 错误: {e}")

    def load_ontology_v2(
        self,
        connection_name: str
    ) -> Optional[Dict[str, Any]]:
        """加载本体从 ontology.json

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
        """检查本体是否存在

        Args:
            connection_name: 数据库连接名

        Returns:
            是否存在
        """
        path = self._get_ontology_file_path(connection_name, for_write=False)
        return path.exists()

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
            "has_ontology_v2": self.ontology_v2_exists(connection_name),
            "has_schema": (conn_dir / "schema.json").exists(),
            "business_context_completed": self.is_business_context_completed(connection_name)
        }
