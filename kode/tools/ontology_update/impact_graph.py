"""
Change Impact Graph

变更影响图：跟踪本体中的依赖关系，计算变更影响范围。
"""

from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict, deque
import json


class ChangeImpactGraph:
    """
    变更影响图

    用于：
    1. 跟踪本体实体之间的依赖关系（类->属性、属性->枚举、度量->聚合等）
    2. 计算变更的影响范围
    3. 决定更新策略（Layer 1/2/3）
    """

    def __init__(self, ontology: Dict[str, Any]):
        """
        初始化影响图

        Args:
            ontology: 本体JSON对象
        """
        self.ontology = ontology
        # 依赖关系图：{entity_id: [dependent_entity_ids]}
        # 例如：{"Class.User": ["Property.User.name", "Property.User.age"]}
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        # 反向依赖图：{entity_id: [entities_that_depend_on_it]}
        self.reverse_dependencies: Dict[str, List[str]] = defaultdict(list)

        # 构建依赖图
        self._build_graph()

    def _build_graph(self):
        """从本体构建依赖图（兼容 V1 和 V2 格式）"""
        classes = self.ontology.get("classes", {})

        # 兼容 V1（字典）和 V2（数组）格式
        if isinstance(classes, dict):
            # V1 格式
            class_items = classes.items()
        elif isinstance(classes, list):
            # V2 格式：classes 是数组，使用 name 或 technical_name 作为 key
            class_items = [
                (cls.get("technical_name") or cls.get("name"), cls) for cls in classes
            ]
        else:
            class_items = []

        # 1. 类 -> 属性依赖
        for class_name, class_def in class_items:
            if not class_name:
                continue

            class_id = f"Class.{class_name}"

            # 类依赖其属性
            properties = class_def.get("properties", {})
            # V2 格式：properties 可能是数组
            if isinstance(properties, list):
                prop_names = [p.get("technical_name") or p.get("name") for p in properties]
            else:
                prop_names = list(properties.keys())

            for prop_name in prop_names:
                if not prop_name:
                    continue
                prop_id = f"Property.{class_name}.{prop_name}"
                self.dependencies[class_id].append(prop_id)
                self.reverse_dependencies[prop_id].append(class_id)

        # 2. 属性 -> 枚举值依赖
        for class_name, class_def in class_items:
            if not class_name:
                continue

            properties = class_def.get("properties", {})

            # V2 格式：properties 可能是数组
            if isinstance(properties, list):
                prop_items = [
                    (p.get("technical_name") or p.get("name"), p) for p in properties
                ]
            else:
                prop_items = properties.items()

            for prop_name, prop_def in prop_items:
                if not prop_name:
                    continue

                prop_id = f"Property.{class_name}.{prop_name}"

                # 如果属性有枚举值
                enum_values = prop_def.get("enum_values", [])
                for enum_val in enum_values:
                    enum_id = f"Enum.{class_name}.{prop_name}.{enum_val.get('value', '')}"
                    self.dependencies[prop_id].append(enum_id)
                    self.reverse_dependencies[enum_id].append(prop_id)

        # 3. 类 -> 关系依赖
        relationships = self.ontology.get("relationships", [])
        for rel in relationships:
            source_class = rel.get("source_class")
            target_class = rel.get("target_class")
            rel_type = rel.get("relationship_type", "")
            rel_id = f"Relationship.{source_class}.{rel_type}.{target_class}"

            # 关系依赖源类和目标类
            source_id = f"Class.{source_class}"
            target_id = f"Class.{target_class}"

            self.dependencies[rel_id].extend([source_id, target_id])
            self.reverse_dependencies[source_id].append(rel_id)
            self.reverse_dependencies[target_id].append(rel_id)

        # 4. 业务规则 -> 相关属性依赖
        rules = self.ontology.get("business_rules", [])
        for rule in rules:
            rule_id = f"Rule.{rule.get('rule_id', '')}"
            related_classes = rule.get("related_classes", [])

            for class_name in related_classes:
                class_id = f"Class.{class_name}"
                self.dependencies[rule_id].append(class_id)
                self.reverse_dependencies[class_id].append(rule_id)

        # 5. 度量指标 -> 类/属性依赖
        metrics = self.ontology.get("metrics", [])
        for metric in metrics:
            metric_id = f"Metric.{metric.get('metric_id', '')}"
            related_classes = metric.get("related_classes", [])

            for class_name in related_classes:
                class_id = f"Class.{class_name}"
                self.dependencies[metric_id].append(class_id)
                self.reverse_dependencies[class_id].append(metric_id)

    def calculate_impact(self, target_path: str, change_type: str) -> Tuple[int, List[str]]:
        """
        计算变更影响

        Args:
            target_path: 目标路径（如 "classes.User.properties.age"）
            change_type: 变更类型

        Returns:
            (impact_score, affected_entities)
            - impact_score: 0-100的影响分数
            - affected_entities: 受影响的实体列表
        """
        # 解析目标路径为实体ID
        entity_id = self._path_to_entity_id(target_path)

        # 使用BFS查找所有受影响的实体
        affected = self._bfs_affected_entities(entity_id)

        # 根据变更类型和影响范围计算影响分数
        impact_score = self._calculate_score(change_type, affected)

        return impact_score, affected

    def _path_to_entity_id(self, path: str) -> str:
        """
        将JSON路径转换为实体ID

        Examples:
            "classes.User" -> "Class.User"
            "classes.User.properties.age" -> "Property.User.age"
            "classes.User.properties.status.enum_values.0" -> "Enum.User.status.active"
        """
        parts = path.split(".")

        if parts[0] == "classes":
            if len(parts) == 2:
                # 类级别
                return f"Class.{parts[1]}"
            elif len(parts) >= 4 and parts[2] == "properties":
                if len(parts) == 4:
                    # 属性级别
                    return f"Property.{parts[1]}.{parts[3]}"
                elif len(parts) >= 6 and parts[4] == "enum_values":
                    # 枚举值级别
                    return f"Enum.{parts[1]}.{parts[3]}.{parts[5]}"

        elif parts[0] == "relationships":
            # 关系级别
            return f"Relationship.{'.'.join(parts[1:])}"

        elif parts[0] == "business_rules":
            return f"Rule.{parts[1]}"

        elif parts[0] == "metrics":
            return f"Metric.{parts[1]}"

        return path  # 默认返回原路径

    def _bfs_affected_entities(self, start_entity: str, max_depth: int = 3) -> List[str]:
        """
        使用BFS查找所有受影响的实体（限制深度）

        Args:
            start_entity: 起始实体ID
            max_depth: 最大查找深度（默认3层）

        Returns:
            受影响的实体ID列表
        """
        visited = set()
        queue = deque([(start_entity, 0)])  # (entity_id, depth)
        affected = []

        while queue:
            entity, depth = queue.popleft()

            if entity in visited or depth > max_depth:
                continue

            visited.add(entity)
            affected.append(entity)

            # 添加所有依赖此实体的其他实体（反向依赖）
            if depth < max_depth:
                for dependent in self.reverse_dependencies.get(entity, []):
                    if dependent not in visited:
                        queue.append((dependent, depth + 1))

        return affected

    def _calculate_score(self, change_type: str, affected_entities: List[str]) -> int:
        """
        计算影响分数（0-100）

        规则：
        - Layer 1 变更（元数据）：基础分10分 + 每个受影响实体5分
        - Layer 2 变更（新增类/属性）：基础分30分 + 每个受影响实体10分
        - Layer 3 变更（合并/拆分）：基础分60分 + 每个受影响实体15分
        """
        # Layer 1 变更类型
        layer1_types = {"add_enum_value", "update_property_desc", "update_class_desc"}
        # Layer 2 变更类型
        layer2_types = {"add_class", "add_property", "add_relationship"}
        # Layer 3 变更类型
        layer3_types = {"merge_classes", "split_class"}

        if change_type in layer1_types:
            base_score = 10
            per_entity_score = 5
        elif change_type in layer2_types:
            base_score = 30
            per_entity_score = 10
        elif change_type in layer3_types:
            base_score = 60
            per_entity_score = 15
        else:
            base_score = 20
            per_entity_score = 8

        # 计算总分（上限100）
        score = base_score + len(affected_entities) * per_entity_score
        return min(score, 100)

    def update_from_change(self, target_path: str, change_type: str, new_value: Any):
        """
        增量更新影响图（当变更应用后调用）

        Args:
            target_path: 目标路径
            change_type: 变更类型
            new_value: 新值
        """
        entity_id = self._path_to_entity_id(target_path)

        # 根据变更类型更新依赖关系
        if change_type == "add_enum_value":
            # 添加枚举值：创建新的 Enum 实体并关联到属性
            parts = target_path.split(".")
            if len(parts) >= 4 and parts[2] == "properties":
                class_name = parts[1]
                prop_name = parts[3]
                prop_id = f"Property.{class_name}.{prop_name}"

                # 新增枚举值ID
                enum_id = f"Enum.{class_name}.{prop_name}.{new_value}"
                if enum_id not in self.dependencies[prop_id]:
                    self.dependencies[prop_id].append(enum_id)
                    self.reverse_dependencies[enum_id].append(prop_id)

        elif change_type == "add_property":
            # 添加属性：创建新的 Property 实体并关联到类
            parts = target_path.split(".")
            if len(parts) >= 4 and parts[2] == "properties":
                class_name = parts[1]
                prop_name = parts[3]
                class_id = f"Class.{class_name}"
                prop_id = f"Property.{class_name}.{prop_name}"

                if prop_id not in self.dependencies[class_id]:
                    self.dependencies[class_id].append(prop_id)
                    self.reverse_dependencies[prop_id].append(class_id)

        elif change_type == "add_class":
            # 添加类：创建新的 Class 实体
            parts = target_path.split(".")
            if len(parts) >= 2 and parts[0] == "classes":
                class_name = parts[1]
                class_id = f"Class.{class_name}"
                # 类实体已存在于图中（通过 _build_graph 初始化）
                # 这里只需确保依赖关系正确
                pass

    def get_related_context(self, target_path: str, context_size: int = 5) -> Dict[str, Any]:
        """
        获取变更的相关上下文（用于AI决策）

        Args:
            target_path: 目标路径
            context_size: 上下文大小（返回最多几个相关实体）

        Returns:
            相关上下文字典，包含：
            - target_entity: 目标实体定义
            - related_properties: 相关属性
            - related_rules: 相关业务规则
            - related_metrics: 相关指标
            - domain_peers: 同领域的其他实体
        """
        entity_id = self._path_to_entity_id(target_path)

        # 获取受影响的实体
        affected = self._bfs_affected_entities(entity_id, max_depth=2)

        # 按类型分类
        related_properties = [e for e in affected if e.startswith("Property.")][:context_size]
        related_rules = [e for e in affected if e.startswith("Rule.")][:context_size]
        related_metrics = [e for e in affected if e.startswith("Metric.")][:context_size]

        # 获取目标实体的定义
        target_entity = self._get_entity_definition(target_path)

        # 获取同领域的其他实体（基于类名前缀）
        domain_peers = self._get_domain_peers(entity_id, context_size)

        return {
            "target_entity": target_entity,
            "related_properties": related_properties,
            "related_rules": related_rules,
            "related_metrics": related_metrics,
            "domain_peers": domain_peers,
        }

    def _get_entity_definition(self, path: str) -> Any:
        """从本体中提取实体定义"""
        parts = path.split(".")
        obj = self.ontology

        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            elif isinstance(obj, list) and part.isdigit():
                obj = obj[int(part)]
            else:
                return None

        return obj

    def _get_domain_peers(self, entity_id: str, limit: int = 5) -> List[str]:
        """
        获取同领域的实体（基于命名前缀）

        Example:
            entity_id = "Class.Sales_Order"
            返回: ["Class.Sales_OrderItem", "Class.Sales_Customer", ...]
        """
        peers = []

        # 提取领域前缀（如 "Sales"）
        parts = entity_id.split(".")
        if len(parts) < 2:
            return []

        entity_name = parts[1]
        domain_prefix = entity_name.split("_")[0] if "_" in entity_name else None

        if not domain_prefix:
            return []

        # 查找所有同前缀的实体
        for dep_id in self.dependencies:
            if dep_id.startswith(parts[0]) and domain_prefix in dep_id:
                if dep_id != entity_id:
                    peers.append(dep_id)
                    if len(peers) >= limit:
                        break

        return peers
