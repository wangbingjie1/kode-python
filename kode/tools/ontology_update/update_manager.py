"""
Ontology Update Manager

本体更新管理器：立即生效 + 异步持久化模式
"""

from typing import Dict, Any, Optional, List
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import copy

from kode.tools.ontology_update.impact_graph import ChangeImpactGraph
from kode.models.ontology_change import ChangeType, ChangeStatus
from kode.utils.logger import get_logger
from kode.utils.context import get_current_user_id

logger = get_logger(__name__)


class Change:
    """变更对象"""

    def __init__(
        self,
        change_type: str,
        target_path: str,
        new_value: Any,
        old_value: Optional[Any] = None,
        user_intent: str = "",
        conversation_id: Optional[int] = None,
    ):
        self.id = f"{int(time.time() * 1000)}_{hash(target_path) % 10000}"
        self.change_type = change_type
        self.target_path = target_path
        self.new_value = new_value
        self.old_value = old_value
        self.user_intent = user_intent
        self.conversation_id = conversation_id
        self.created_at = datetime.now()


class OntologyUpdateManager:
    """
    本体更新管理器：立即生效 + 立即持久化

    核心特性：
    1. 变更立即应用到内存中的本体
    2. 后续操作立即看到变更效果
    3. 每次变更立即触发磁盘写入（异步，不阻塞用户）
    4. 自动创建版本快照（异步）
    5. 数据库记录异步执行

    持久化策略：
    - 每次变更都立即写盘（确保数据安全）
    - 磁盘写入在后台线程执行（不影响响应速度）
    - 同时创建版本快照到 versions/ 目录
    """

    # 类级别的锁（用于多线程安全）
    _lock = threading.Lock()

    def __init__(self, connection_name: str, ontology_path: str):
        """
        初始化更新管理器

        Args:
            connection_name: 数据库连接名称
            ontology_path: 本体文件路径
        """
        self.connection_name = connection_name
        self.ontology_path = Path(ontology_path)

        # 加载本体到内存
        self.ontology = self._load_ontology()

        # 构建影响图
        self.impact_graph = ChangeImpactGraph(self.ontology)

        # 待写入磁盘的变更队列（用于生成变更摘要）
        self.pending_writes: List[Change] = []

        # 上次磁盘写入时间（用于统计）
        self.last_disk_write = time.time()

        # 变更计数（用于统计）
        self.change_count = 0

        # 版本管理相关
        self.last_version_created = None  # 上次创建的版本号

    def _load_ontology(self) -> Dict[str, Any]:
        """从磁盘加载本体到内存"""
        if not self.ontology_path.exists():
            logger.warning(f"⚠️ 本体文件不存在: {self.ontology_path}")

            # 安全检查：确保这是一个本体文件
            if not str(self.ontology_path).endswith("ontology.json"):
                raise ValueError(
                    f"❌ 错误的本体文件路径: {self.ontology_path}。"
                    f"只支持 ontology.json 文件。"
                )

            # 创建符合格式的空本体
            logger.info("创建新的空本体")
            return {
                "version": "3.0",
                "meta": {
                    "ontology_name": f"{self.connection_name}_Ontology",
                    "created_at": datetime.now().isoformat(),
                    "source_connection": self.connection_name,
                    "domains": []
                },
                "schema": {
                    "classes": {},
                    "relationships": []
                },
                "business_rules": [],
                "metrics": []
            }

        try:
            with open(self.ontology_path, "r", encoding="utf-8") as f:
                ontology = json.load(f)
            logger.info(f"✅ 已加载本体: {self.ontology_path}（{len(json.dumps(ontology))} bytes）")
            return ontology
        except Exception as e:
            logger.error(f"❌ 加载本体失败: {e}")
            raise

    def apply_change(self, change: Change) -> Dict[str, Any]:
        """
        立即应用变更到内存本体

        Args:
            change: 变更对象

        Returns:
            应用结果字典
        """
        with self._lock:
            try:
                # 1. 计算影响
                impact_score, affected_entities = self.impact_graph.calculate_impact(
                    change.target_path, change.change_type
                )

                logger.info(
                    f"📊 变更影响分析: type={change.change_type}, "
                    f"path={change.target_path}, "
                    f"score={impact_score}, "
                    f"affected={len(affected_entities)}"
                )

                # 2. 立即修改内存中的本体
                if change.change_type in ["add_enum_value", "update_property_desc", "update_class_desc", "update_class_mapping", "update_column_mapping"]:
                    # Layer 1: 直接JSON操作（<10ms）
                    self._apply_metadata_change(change)
                elif change.change_type in ["add_class", "add_property", "add_relationship"]:
                    # Layer 2: 添加新实体（也是JSON操作，但需要更新影响图）
                    self._apply_entity_addition(change)
                elif change.change_type == "move_table_domain":
                    # Layer 2.5: Domain 级别的表迁移
                    self._apply_domain_change(change)
                else:
                    # 其他复杂变更
                    self._apply_complex_change(change)

                # 3. 增量更新影响图
                self.impact_graph.update_from_change(
                    change.target_path, change.change_type, change.new_value
                )

                # 4. 加入待写磁盘队列
                self.pending_writes.append(change)
                self.change_count += 1

                # 5. 智能触发磁盘写入
                self._trigger_disk_write_if_needed(change.change_type)

                logger.info(f"✅ 变更已立即生效: {change.id}")

                return {
                    "status": "success",
                    "applied": True,
                    "change_id": change.id,
                    "impact_score": impact_score,
                    "affected_entities": affected_entities,
                }

            except Exception as e:
                logger.error(f"❌ 应用变更失败: {e}")
                return {
                    "status": "error",
                    "applied": False,
                    "error": str(e),
                }

    def _get_class_by_name(self, class_name: str, domain: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据类名获取类定义（兼容 V1、V2 和 V3 格式）

        V1 格式: {"classes": {"User": {...}}}  # 字典
        V2 格式: {"classes": [{"name": "用户", "technical_name": "users", ...}]}  # 数组
        V3 格式: {"schema": {"classes": {"domain": {"table_name": {...}}}}}  # 嵌套字典

        Args:
            class_name: 类名（可能是中文名或技术名）
            domain: 域名（V3格式需要）

        Returns:
            类定义字典，如果不存在返回 None
        """
        version = self.ontology.get("version", "1.0")

        # V3 格式：嵌套在 schema.classes 下
        if version.startswith("3"):
            schema = self.ontology.get("schema", {})
            classes = schema.get("classes", {})

            if not isinstance(classes, dict):
                return None

            # 如果提供了域名，直接查找
            if domain and domain in classes:
                domain_tables = classes[domain]
                if isinstance(domain_tables, dict) and class_name in domain_tables:
                    return domain_tables[class_name]

            # 否则遍历所有域
            for domain_name, domain_tables in classes.items():
                if isinstance(domain_tables, dict) and class_name in domain_tables:
                    return domain_tables[class_name]

            return None

        # V1/V2 格式
        classes = self.ontology.get("classes", {})

        # V1 格式：classes 是字典
        if isinstance(classes, dict):
            return classes.get(class_name)

        # V2 格式：classes 是数组
        elif isinstance(classes, list):
            for cls in classes:
                # 尝试匹配中文名或技术名
                if cls.get("name") == class_name or cls.get("technical_name") == class_name:
                    return cls
            return None

        return None

    def _get_property_by_name(self, class_def: Dict[str, Any], prop_name: str) -> Optional[Dict[str, Any]]:
        """
        根据属性名获取属性定义（兼容 V1、V2 和 V3 格式）

        V1 格式: {"properties": {"age": {...}}}  # 字典
        V2 格式: {"properties": [{"name": "年龄", "technical_name": "age", ...}]}  # 数组
        V3 格式: {"attributes": {"field_name": {...}}}  # 字典

        Args:
            class_def: 类定义
            prop_name: 属性名（可能是中文名或技术名）

        Returns:
            属性定义字典，如果不存在返回 None
        """
        if not class_def:
            return None

        # V3 格式：使用 attributes 字段
        attributes = class_def.get("attributes", {})
        if isinstance(attributes, dict) and prop_name in attributes:
            return attributes[prop_name]

        # V1/V2 格式：使用 properties 字段
        properties = class_def.get("properties", {})

        # V1 格式：properties 是字典
        if isinstance(properties, dict):
            return properties.get(prop_name)

        # V2 格式：properties 是数组
        elif isinstance(properties, list):
            for prop in properties:
                # 尝试匹配中文名或技术名
                if prop.get("name") == prop_name or prop.get("technical_name") == prop_name:
                    return prop
            return None

        return None

    def _apply_metadata_change(self, change: Change):
        """
        应用元数据层变更（Layer 1）

        支持：
        - add_enum_value: 添加枚举值
        - update_property_desc: 更新属性描述
        - update_class_desc: 更新类描述
        - update_class_mapping: 更新类的表映射
        - update_column_mapping: 更新属性的字段映射

        路径格式：
        - V1/V2: classes.{class_name}.description
        - V3: schema.classes.{domain}.{table}.description
        """
        parts = change.target_path.split(".")
        version = self.ontology.get("version", "1.0")
        is_v3 = version.startswith("3")

        if change.change_type == "add_enum_value":
            # V3 路径: schema.classes.{domain}.{table}.attributes.{field}.enum_mapping
            # V1/V2 路径: classes.{class}.properties.{field}.enum_mapping

            # 判断目标字段是 enum_values 还是 enum_mapping
            target_field = parts[-1] if parts[-1] in ["enum_values", "enum_mapping"] else "enum_values"

            if is_v3 and parts[0] == "schema" and parts[1] == "classes":
                # V3 格式: schema.classes.{domain}.{table}.attributes.{field}.{target_field}
                domain = parts[2]
                table_name = parts[3]
                field_name = parts[5]

                prop_def = (
                    self.ontology.get("schema", {})
                    .get("classes", {})
                    .get(domain, {})
                    .get(table_name, {})
                    .get("attributes", {})
                    .get(field_name, {})
                )
            elif len(parts) >= 5 and parts[0] == "classes" and parts[2] == "properties":
                # V1/V2 格式: classes.{class}.properties.{field}.{target_field}
                # 但如果当前是 V3 格式，需要自动查找 domain
                class_name = parts[1]
                prop_name = parts[3]

                if is_v3:
                    # 自动查找 class_name 所在的 domain
                    schema_classes = self.ontology.get("schema", {}).get("classes", {})
                    prop_def = None

                    for domain_name, domain_tables in schema_classes.items():
                        if class_name in domain_tables:
                            prop_def = (
                                domain_tables.get(class_name, {})
                                .get("attributes", {})
                                .get(prop_name, {})
                            )
                            if prop_def:
                                logger.info(f"🔍 自动查找到表: {class_name} 位于域 {domain_name}")
                                break

                    if not prop_def:
                        prop_def = {}
                        logger.warning(f"⚠️ 未找到表: {class_name}")
                else:
                    # V1/V2 格式
                    prop_def = (
                        self.ontology.get("classes", {})
                        .get(class_name, {})
                        .get("properties", {})
                        .get(prop_name, {})
                    )
            else:
                prop_def = {}

            if prop_def:
                # 处理 enum_mapping（字典格式）或 enum_values（数组格式）
                if target_field == "enum_mapping":
                    # enum_mapping 是字典格式：{"1": "正常消耗", "2": "已使用"}
                    if "enum_mapping" not in prop_def:
                        prop_def["enum_mapping"] = {}

                    # new_value 应该是字典
                    if isinstance(change.new_value, dict):
                        prop_def["enum_mapping"].update(change.new_value)
                        logger.info(f"✅ 已更新枚举映射: {change.target_path} = {change.new_value}")
                else:
                    # enum_values 是数组格式（旧逻辑）
                    if "enum_values" not in prop_def:
                        prop_def["enum_values"] = []

                    existing_values = [ev.get("value") for ev in prop_def["enum_values"]]
                    new_val = change.new_value if isinstance(change.new_value, dict) else {"value": change.new_value}

                    if new_val.get("value") not in existing_values:
                        prop_def["enum_values"].append(new_val)
                        logger.info(f"✅ 已添加枚举值: {change.target_path} += {new_val}")

        elif change.change_type == "update_property_desc":
            # V3 路径: schema.classes.{domain}.{table}.attributes.{field}.constraint
            # V1/V2 路径: classes.{class}.properties.{field}.description
            if is_v3 and parts[0] == "schema" and parts[1] == "classes":
                # V3 格式: schema.classes.domain.table.attributes.field.constraint
                domain = parts[2]
                table_name = parts[3]
                field_name = parts[5]
                target_field = parts[6] if len(parts) > 6 else "constraint"

                prop_def = (
                    self.ontology.get("schema", {})
                    .get("classes", {})
                    .get(domain, {})
                    .get(table_name, {})
                    .get("attributes", {})
                    .get(field_name, {})
                )

                if prop_def:
                    change.old_value = prop_def.get(target_field)
                    prop_def[target_field] = change.new_value
                    logger.info(f"✅ 已更新属性描述 (V3): {domain}.{table_name}.{field_name}.{target_field}")
            elif len(parts) >= 5 and parts[0] == "classes" and parts[2] == "properties":
                class_name = parts[1]
                prop_name = parts[3]
                field_name = parts[4] if len(parts) > 4 else "business_description"

                prop_def = (
                    self.ontology.get("classes", {})
                    .get(class_name, {})
                    .get("properties", {})
                    .get(prop_name, {})
                )

                if prop_def:
                    change.old_value = prop_def.get(field_name)
                    prop_def[field_name] = change.new_value
                    logger.info(f"✅ 已更新属性描述: {class_name}.{prop_name}.{field_name}")

        elif change.change_type == "update_class_desc":
            # V3 路径: schema.classes.{domain}.{table}.description
            # V1/V2 路径: classes.{class}.description 或 classes.{class}.business_description
            if is_v3 and parts[0] == "schema" and parts[1] == "classes":
                # V3 格式路径
                domain = parts[2]
                table_name = parts[3]
                field_name = parts[4] if len(parts) > 4 else "description"

                class_def = (
                    self.ontology.get("schema", {})
                    .get("classes", {})
                    .get(domain, {})
                    .get(table_name, {})
                )

                if class_def:
                    change.old_value = class_def.get(field_name)
                    class_def[field_name] = change.new_value
                    logger.info(f"✅ 已更新类描述 (V3): {domain}.{table_name}.{field_name}")
                else:
                    logger.warning(f"⚠️ V3 类 {domain}.{table_name} 不存在，无法更新描述")
            elif len(parts) >= 3 and parts[0] == "classes":
                # V1/V2 格式路径，但本体可能是 V3
                class_name = parts[1]
                # 从路径提取的字段名（可能是 description 或 business_description）
                path_field_name = parts[2] if len(parts) > 2 else "description"

                class_def = self._get_class_by_name(class_name)

                if class_def:
                    # V3 本体统一使用 "description" 字段，忽略路径中的 business_description
                    # V1/V2 本体则使用路径中指定的字段名
                    if is_v3:
                        field_name = "description"
                    else:
                        field_name = path_field_name

                    change.old_value = class_def.get(field_name)
                    class_def[field_name] = change.new_value
                    logger.info(f"✅ 已更新类描述: {class_name}.{field_name} (路径字段: {path_field_name})")
                else:
                    logger.warning(f"⚠️ 类 {class_name} 不存在，无法更新描述")

        elif change.change_type == "update_class_mapping":
            # 路径示例: classes.订单.table_mapping
            if len(parts) >= 3 and parts[0] == "classes":
                class_name = parts[1]
                field_name = parts[2]  # table_mapping

                class_def = self._get_class_by_name(class_name)

                if class_def:
                    change.old_value = class_def.get(field_name)
                    class_def[field_name] = change.new_value
                    logger.info(f"✅ 已更新类表映射: {class_name}.{field_name} = {change.new_value}")
                else:
                    logger.warning(f"⚠️ 类 {class_name} 不存在，无法更新表映射")

        elif change.change_type == "update_column_mapping":
            # 路径示例: classes.订单.properties.status.column_mapping
            if len(parts) >= 5 and parts[0] == "classes" and parts[2] == "properties":
                class_name = parts[1]
                prop_name = parts[3]
                field_name = parts[4]  # column_mapping

                class_def = self._get_class_by_name(class_name)
                prop_def = self._get_property_by_name(class_def, prop_name)

                if prop_def:
                    change.old_value = prop_def.get(field_name)
                    prop_def[field_name] = change.new_value
                    logger.info(f"✅ 已更新属性字段映射: {class_name}.{prop_name}.{field_name} = {change.new_value}")
                else:
                    logger.warning(f"⚠️ 属性 {class_name}.{prop_name} 不存在，无法更新字段映射")

    def _apply_entity_addition(self, change: Change):
        """
        应用实体添加变更（Layer 2）

        支持：
        - add_class: 添加新类
        - add_property: 添加新属性
        - add_relationship: 添加新关系
        """
        parts = change.target_path.split(".")

        if change.change_type == "add_class":
            # 路径示例: classes.NewClass
            if len(parts) >= 2 and parts[0] == "classes":
                class_name = parts[1]
                if "classes" not in self.ontology:
                    self.ontology["classes"] = {}

                if class_name not in self.ontology["classes"]:
                    # new_value 应该是完整的类定义
                    self.ontology["classes"][class_name] = change.new_value
                    logger.info(f"✅ 已添加新类: {class_name}")

        elif change.change_type == "add_property":
            # 路径示例: classes.User.properties.new_field
            if len(parts) >= 4 and parts[0] == "classes" and parts[2] == "properties":
                class_name = parts[1]
                prop_name = parts[3]

                class_def = self.ontology.get("classes", {}).get(class_name, {})
                if class_def:
                    if "properties" not in class_def:
                        class_def["properties"] = {}

                    if prop_name not in class_def["properties"]:
                        # new_value 应该是完整的属性定义
                        class_def["properties"][prop_name] = change.new_value
                        logger.info(f"✅ 已添加新属性: {class_name}.{prop_name}")

        elif change.change_type == "add_relationship":
            # 路径示例: relationships.{index}
            if "relationships" not in self.ontology:
                self.ontology["relationships"] = []

            # new_value 应该是完整的关系定义
            self.ontology["relationships"].append(change.new_value)
            logger.info(f"✅ 已添加新关系: {change.new_value.get('relationship_type')}")

    def _apply_complex_change(self, change: Change):
        """应用复杂变更（Layer 3）"""
        # TODO: 实现合并类、拆分类等复杂变更
        logger.warning(f"⚠️ 复杂变更暂未实现: {change.change_type}")

    def _trigger_disk_write_if_needed(self, change_type: str):
        """
        每次变更立即触发磁盘写入

        策略：立即持久化（不等待累积）
        - 确保数据安全：每次变更都立即保存到磁盘
        - 异步执行：在后台线程中写入，不阻塞用户操作
        - 自动版本快照：同时创建版本历史记录
        """
        logger.info(f"🔄 立即触发磁盘写入（变更类型: {change_type}）")

        # 异步写入（不阻塞当前线程）
        threading.Thread(target=self._write_to_disk, daemon=True).start()

    def _write_to_disk(self):
        """异步写入本体到磁盘 + 创建版本"""
        try:
            # 使用 JSON 序列化来创建副本（避免 deepcopy 的线程锁问题）
            ontology_json = json.dumps(self.ontology, ensure_ascii=False)
            ontology_copy = json.loads(ontology_json)

            # 写入主文件（ontology.json）
            with open(self.ontology_path, "w", encoding="utf-8") as f:
                json.dump(ontology_copy, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 本体已写入磁盘: {self.ontology_path}")

            # 2. 创建版本快照（异步）
            self._create_version_snapshot(ontology_copy)

            # 更新状态
            self.last_disk_write = time.time()
            self.change_count = 0
            self.pending_writes.clear()

        except Exception as e:
            logger.error(f"❌ 写入磁盘失败: {e}")

    def _create_version_snapshot(self, ontology_data: Dict[str, Any]):
        """创建版本快照（异步）"""
        try:
            from kode.services.ontology_version_manager import OntologyVersionManager
            from kode.database.session import async_session_maker
            import asyncio

            user_id = get_current_user_id()

            # 生成变更摘要
            change_summary = self._generate_change_summary()

            # 创建异步任务
            async def _async_create_version():
                async with async_session_maker() as session:
                    version_manager = OntologyVersionManager()
                    version = await version_manager.create_version(
                        session=session,
                        user_id=user_id,
                        connection_name=self.connection_name,
                        ontology_data=ontology_data,
                        change_summary=change_summary,
                        conversation_id=None,  # TODO: 从 context 获取
                        is_snapshot=True
                    )
                    self.last_version_created = version.version_number
                    logger.info(f"📦 自动创建版本快照: v{version.version_number}")
                    return version.version_number

            # 在新事件循环中运行（避免阻塞）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            version_number = loop.run_until_complete(_async_create_version())
            loop.close()
            logger.info(f"✅ 版本快照创建成功: v{version_number}")

        except Exception as e:
            logger.error(f"❌ 创建版本快照失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _generate_change_summary(self) -> str:
        """根据待处理变更生成摘要"""
        if not self.pending_writes:
            return "自动保存"

        change_types = [c.change_type for c in self.pending_writes]
        type_counts = {}
        for ct in change_types:
            type_counts[ct] = type_counts.get(ct, 0) + 1

        summary_parts = []
        for ct, count in type_counts.items():
            summary_parts.append(f"{ct}({count})")

        return f"批量变更: {', '.join(summary_parts)}"

    def get_ontology(self) -> Dict[str, Any]:
        """获取当前内存中的本体（最新版本）"""
        return self.ontology

    def force_flush(self):
        """强制刷新到磁盘（同步操作）"""
        with self._lock:
            self._write_to_disk()

    def _apply_domain_change(self, change: Change):
        """
        应用 Domain 级别的变更（Layer 2.5）

        支持：
        - move_table_domain: 将表从一个 Domain 移动到另一个 Domain

        change.new_value 格式:
        {
            "table_name": "user",
            "from_domain": "user_management",
            "to_domain": "order_payment"
        }
        """
        if change.change_type == "move_table_domain":
            # 从 new_value 获取参数
            table_name = change.new_value.get("table_name")
            from_domain = change.new_value.get("from_domain")
            to_domain = change.new_value.get("to_domain")

            if not all([table_name, from_domain, to_domain]):
                logger.error(f"❌ move_table_domain 参数不完整: {change.new_value}")
                return

            version = self.ontology.get("version", "1.0")
            if not version.startswith("3"):
                logger.error(f"❌ move_table_domain 仅支持 V3 格式本体")
                return

            schema = self.ontology.get("schema", {})
            classes = schema.get("classes", {})

            # 验证源 domain 和表存在
            if from_domain not in classes:
                logger.error(f"❌ 源 Domain '{from_domain}' 不存在")
                return

            if table_name not in classes[from_domain]:
                logger.error(f"❌ 表 '{table_name}' 在 Domain '{from_domain}' 中不存在")
                return

            # 创建目标 domain（如果不存在）
            if to_domain not in classes:
                logger.info(f"目标 Domain '{to_domain}' 不存在，自动创建")
                classes[to_domain] = {}

            # 1. 移动表定义
            logger.info(f"移动表定义: {table_name}")
            table_def = classes[from_domain].pop(table_name)
            classes[to_domain][table_name] = table_def

            # 2. 更新 relationships
            relationships = schema.get("relationships", {})
            updated_rels = 0

            for rel_id, rel_data in relationships.items():
                from_class = rel_data.get("from", "") or rel_data.get("from_class", "")
                to_class = rel_data.get("to", "") or rel_data.get("to_class", "")

                if from_class == table_name and "from_domain" in rel_data:
                    rel_data["from_domain"] = to_domain
                    updated_rels += 1

                if to_class == table_name and "to_domain" in rel_data:
                    rel_data["to_domain"] = to_domain
                    updated_rels += 1

            logger.info(f"更新了 {updated_rels} 个关系引用")

            # 3. 更新 properties
            properties = schema.get("properties", {})
            updated_props = 0

            for prop_name, prop_data in properties.items():
                used_by = prop_data.get("used_by", [])
                new_used_by = []

                for usage in used_by:
                    if "." in usage:
                        parts = usage.split(".", 1)
                        if parts[0] == from_domain and parts[1].split(".")[0] == table_name:
                            new_used_by.append(f"{to_domain}.{parts[1]}")
                            updated_props += 1
                        else:
                            new_used_by.append(usage)
                    else:
                        new_used_by.append(usage)

                prop_data["used_by"] = new_used_by

            logger.info(f"更新了 {updated_props} 个共享属性引用")

            # 4. 更新 uncertainties
            uncertainties = self.ontology.get("uncertainties", [])
            updated_ucs = 0

            for uc in uncertainties:
                entity = uc.get("entity", "")
                if entity.startswith(f"{from_domain}.{table_name}"):
                    uc["entity"] = entity.replace(
                        f"{from_domain}.{table_name}",
                        f"{to_domain}.{table_name}",
                        1
                    )
                    if uc.get("domain") == from_domain:
                        uc["domain"] = to_domain
                    updated_ucs += 1

            logger.info(f"更新了 {updated_ucs} 个不确定性记录")

            # 5. 更新 meta.domains
            if to_domain not in self.ontology.get("meta", {}).get("domains", []):
                logger.info(f"将 {to_domain} 添加到 meta.domains")
                if "meta" not in self.ontology:
                    self.ontology["meta"] = {}
                if "domains" not in self.ontology["meta"]:
                    self.ontology["meta"]["domains"] = []
                self.ontology["meta"]["domains"].append(to_domain)

            logger.info(f"✅ 成功将表 '{table_name}' 从 '{from_domain}' 迁移到 '{to_domain}'")
