"""
Ontology Update Tool

本体增量更新工具：支持通过对话方式更新本体
"""

from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field, PrivateAttr
import json
import threading
from pathlib import Path

from kode.tools.base import KodeTool
from kode.tools.ontology_update.update_manager import OntologyUpdateManager, Change
from kode.utils.logger import get_logger
from kode.utils.context import get_current_user_id
from kode.utils.path_utils import get_safe_connection_path
from kode.utils.config import ConfigManager
from kode.database.session import SessionLocal
from kode.models.ontology_change import OntologyChange, ChangeType, ChangeStatus

logger = get_logger(__name__)

# 全局管理器缓存（避免 Pydantic 序列化问题）
_GLOBAL_MANAGERS: Dict[str, OntologyUpdateManager] = {}
_GLOBAL_LOCK = threading.Lock()


class OntologyUpdateToolInput(BaseModel):
    """本体更新工具输入参数"""

    connection_name: str = Field(description="数据库连接名称")
    change_type: str = Field(
        description=(
            "变更类型，支持：\n"
            "- add_enum_value: 添加枚举值\n"
            "- update_property_desc: 更新属性描述\n"
            "- update_class_desc: 更新类描述\n"
            "- update_class_mapping: 更新类的表映射（当用户指出查错表时）\n"
            "- update_column_mapping: 更新属性的字段映射（当用户指出字段错误时）\n"
            "- move_table_domain: 将表从一个 Domain 移动到另一个 Domain\n"
            "- add_class: 添加新类\n"
            "- add_property: 添加新属性\n"
            "- add_relationship: 添加新关系"
        )
    )
    target_path: str = Field(
        description=(
            "目标路径（JSON path格式）。\n"
            "V1/V2 格式示例：\n"
            "- 'classes.User.properties.age.description' (属性描述)\n"
            "- 'classes.Order.description' (类描述，注意使用 description 而非 business_description)\n"
            "- 'classes.Product.properties.status.enum_values' (枚举值)\n"
            "注意：更新类描述时请使用 'classes.表名.description' 格式"
        )
    )
    new_value: Any = Field(description="新值（JSON格式）。可以是字符串、字典或列表")
    old_value: Optional[Any] = Field(
        default=None, description="旧值（用于冲突检测，可选）"
    )
    user_intent: str = Field(
        default="", description="用户意图描述（用于记录和反思）"
    )
    conversation_id: Optional[int] = Field(
        default=None, description="对话ID（如果通过对话触发）"
    )


class OntologyUpdateTool(KodeTool):
    """
    本体更新工具

    功能：
    1. 接收用户的本体修改请求
    2. 立即应用变更到内存本体
    3. 异步持久化到磁盘
    4. 记录变更到数据库（用于审计和反思）

    使用场景：
    - 用户通过对话补充枚举值："订单状态还有'已取消'这个选项"
    - 用户纠正业务描述："这个字段不是年龄，是用户等级"
    - 用户添加新的业务规则
    """

    name: str = "OntologyUpdateTool"
    description: str = (
        "更新数据库的业务本体（Ontology）。\n"
        "支持添加枚举值、更新业务描述、添加新类/属性/关系等。\n"
        "变更会立即生效，后续查询会看到更新后的结果。\n\n"
        "**使用时机**：\n"
        "1. 用户补充或纠正业务知识（如枚举值、字段含义）\n"
        "2. 用户添加新的业务规则或指标定义\n"
        "3. 用户要求扩展本体（添加新类、新属性）\n\n"
        "**变更类型说明**：\n"
        "- add_enum_value: 为枚举字段添加新的取值选项\n"
        "- update_property_desc: 修正字段的业务含义描述\n"
        "- update_class_desc: 修正表的业务含义描述\n"
        "- update_class_mapping: 修正类的数据库表映射（当用户指出查错表时）\n"
        "- update_column_mapping: 修正属性的数据库字段映射（当用户指出字段错误时）\n"
        "- move_table_domain: 将表从一个 Domain 移动到另一个 Domain（用户说'XX表应该属于YY域'）\n"
        "- add_class: 添加新的业务实体（表）\n"
        "- add_property: 为实体添加新字段\n"
        "- add_relationship: 定义实体间的新关系"
    )
    args_schema: Type[BaseModel] = OntologyUpdateToolInput
    requires_permission: bool = False  # 自动更新，不需要用户确认

    def _get_manager(self, connection_name: str) -> OntologyUpdateManager:
        """
        获取或创建更新管理器（单例模式）

        Args:
            connection_name: 数据库连接名称

        Returns:
            OntologyUpdateManager实例
        """
        global _GLOBAL_MANAGERS, _GLOBAL_LOCK

        # 获取用户 ID 用于隔离
        user_id = get_current_user_id()
        cache_key = f"{user_id}/{connection_name}"

        with _GLOBAL_LOCK:
            if cache_key not in _GLOBAL_MANAGERS:
                # 获取配置的 ontology_path
                config = ConfigManager()
                ontology_store_path = config.get("storage.ontology_path", "./ontology_store")

                # 确定本体文件路径（只使用 v3，v2 已废弃）
                # 使用用户隔离路径：ontology_store/{user_id}/{connection_name}/
                safe_conn_name = get_safe_connection_path(connection_name)
                ontology_base = Path(ontology_store_path) / user_id / safe_conn_name
                ontology_path = ontology_base / "ontology_v3.json"

                # 确保父目录存在
                if not ontology_path.exists():
                    logger.warning(f"⚠️ 本体文件不存在: {ontology_path}，将创建新本体")
                    ontology_base.mkdir(parents=True, exist_ok=True)

                # 创建管理器
                manager = OntologyUpdateManager(connection_name, str(ontology_path))
                _GLOBAL_MANAGERS[cache_key] = manager
                logger.info(f"✅ 创建本体更新管理器: {cache_key}")

            return _GLOBAL_MANAGERS[cache_key]

    def _run(
        self,
        connection_name: str,
        change_type: str,
        target_path: str,
        new_value: Any,
        old_value: Optional[Any] = None,
        user_intent: str = "",
        conversation_id: Optional[int] = None,
    ) -> str:
        """
        执行本体更新（立即生效）

        Args:
            connection_name: 数据库连接名称
            change_type: 变更类型
            target_path: 目标路径
            new_value: 新值
            old_value: 旧值（可选）
            user_intent: 用户意图
            conversation_id: 对话ID

        Returns:
            更新结果（JSON字符串）
        """
        try:
            # 获取用户 ID
            user_id = get_current_user_id()

            # 1. 获取更新管理器
            manager = self._get_manager(connection_name)

            # 2. 创建变更对象
            change = Change(
                change_type=change_type,
                target_path=target_path,
                new_value=new_value,
                old_value=old_value,
                user_intent=user_intent,
                conversation_id=conversation_id,
            )

            # 3. 立即应用变更（内存操作）
            result = manager.apply_change(change)

            if not result.get("applied"):
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"变更应用失败: {result.get('error')}",
                    },
                    ensure_ascii=False,
                )

            # 4. 异步记录到数据库
            threading.Thread(
                target=self._record_change_to_db,
                args=(change, connection_name, result, user_id),
                daemon=True,
            ).start()

            # 5. 返回成功结果
            return json.dumps(
                {
                    "status": "success",
                    "applied": True,
                    "change_id": change.id,
                    "impact_score": result.get("impact_score", 0),
                    "affected_entities_count": len(result.get("affected_entities", [])),
                    "message": f"✅ 变更已应用并立即生效",
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"❌ OntologyUpdateTool 执行失败: {e}", exc_info=True)
            return json.dumps(
                {"status": "error", "message": f"执行失败: {str(e)}"},
                ensure_ascii=False,
            )

    def _record_change_to_db(
        self, change: Change, connection_name: str, result: Dict[str, Any], user_id: str
    ):
        """
        异步记录变更到数据库

        Args:
            change: 变更对象
            connection_name: 连接名称
            result: 应用结果
            user_id: 用户 ID
        """
        try:
            # 使用同步 Session
            db = SessionLocal()

            # 创建变更记录
            db_change = OntologyChange(
                user_id=user_id,
                connection_name=connection_name,
                conversation_id=change.conversation_id,
                change_type=ChangeType[change.change_type.upper()],
                target_path=change.target_path,
                old_value=change.old_value,
                new_value=change.new_value,
                user_intent=change.user_intent,
                context={
                    "affected_entities": result.get("affected_entities", []),
                },
                impact_score=result.get("impact_score", 0),
                affected_entities=result.get("affected_entities", []),
                status=ChangeStatus.APPLIED,
                applied_at=change.created_at,
            )

            db.add(db_change)
            db.commit()
            logger.info(f"📝 变更已记录到数据库: {change.id}")

        except Exception as e:
            logger.error(f"❌ 记录变更到数据库失败: {e}")
        finally:
            db.close()

    def get_recent_changes(self, connection_name: str, limit: int = 10) -> str:
        """
        获取最近的变更历史

        Args:
            connection_name: 数据库连接名称
            limit: 返回数量

        Returns:
            变更历史（JSON字符串）
        """
        try:
            db = SessionLocal()
            changes = (
                db.query(OntologyChange)
                .filter(OntologyChange.connection_name == connection_name)
                .order_by(OntologyChange.created_at.desc())
                .limit(limit)
                .all()
            )

            return json.dumps(
                {
                    "status": "success",
                    "changes": [c.to_dict() for c in changes],
                },
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"❌ 获取变更历史失败: {e}")
            return json.dumps(
                {"status": "error", "message": str(e)}, ensure_ascii=False
            )
        finally:
            db.close()

    def force_flush_all(self):
        """强制将所有管理器的变更刷新到磁盘"""
        global _GLOBAL_MANAGERS, _GLOBAL_LOCK

        with _GLOBAL_LOCK:
            for conn_name, manager in _GLOBAL_MANAGERS.items():
                logger.info(f"🔄 强制刷新: {conn_name}")
                manager.force_flush()
