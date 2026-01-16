"""
Ontology Visualization API Routes

将后端本体数据转换为前端可视化格式的 REST API 端点。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kode.database.session import get_db
from kode.models.user import User
from kode.models.project import Project
from kode.models.project_data_source import ProjectDataSource, ProjectDataSourceStatus
from kode.models.data_source import DataSource
from kode.models.project_ontology import ProjectOntology
from kode.utils.config import ConfigManager
from kode.utils.path_utils import get_safe_connection_path
from kode.web.dependencies import get_current_user
from kode.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/projects", tags=["ontology-visualization"])


# ============ Pydantic Schemas ============


class OntologyNodeProperties(BaseModel):
    """节点属性"""
    description: Optional[str] = None
    importance: Optional[str] = None
    domain: Optional[str] = None
    class_type: Optional[str] = None
    attribute_count: Optional[int] = None
    lifecycle_states: Optional[List[str]] = None
    why: Optional[str] = None


class OntologyNode(BaseModel):
    """本体可视化节点"""
    id: str
    label: str
    type: str  # "DataSet", "Entity", "Metric", "BusinessRule", "Domain" 等
    domain: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class OntologyRelation(BaseModel):
    """本体可视化关系"""
    id: Optional[str] = None
    source: str  # from
    target: str  # to
    type: str  # "HAS_ONE", "HAS_MANY", "BELONGS_TO" 等
    properties: Optional[Dict[str, Any]] = None


class OntologyVisualizationResponse(BaseModel):
    """本体可视化响应"""
    nodes: List[OntologyNode]
    relations: List[OntologyRelation]
    meta: Dict[str, Any] = Field(default_factory=dict)
    statistics: Dict[str, int] = Field(default_factory=dict)


class OntologyVisualizationError(BaseModel):
    """错误响应"""
    detail: str
    code: str


# ============ Helper Functions ============


def _determine_node_type(class_data: Dict[str, Any], class_name: str) -> str:
    """
    根据 class 数据确定节点类型

    映射规则：
    - 包含订单/支付相关 -> Order
    - 包含用户相关 -> User
    - 包含产品/商品相关 -> Product
    - 包含设备/设置相关 -> Config
    - 包含日志/记录相关 -> Log
    - 默认 -> Entity
    """
    importance = class_data.get("importance", "")
    description = class_data.get("description", "").lower()
    name_lower = class_name.lower()

    # 按重要性和关键词判断类型
    if importance == "critical":
        if any(kw in name_lower for kw in ["order", "payment", "transaction"]):
            return "Order"
        if any(kw in name_lower for kw in ["user", "account", "member"]):
            return "User"
        return "Entity"

    if any(kw in name_lower for kw in ["order", "payment", "transaction", "charge", "refund"]):
        return "Order"

    if any(kw in name_lower for kw in ["user", "account", "member", "profile"]):
        return "User"

    if any(kw in name_lower for kw in ["product", "sku", "item", "goods"]):
        return "Product"

    if any(kw in name_lower for kw in ["config", "setting", "option", "preference"]):
        return "Config"

    if any(kw in name_lower for kw in ["log", "record", "history", "audit", "detail"]):
        return "Log"

    if any(kw in name_lower for kw in ["metric", "kpi", "measure"]):
        return "Metric"

    if any(kw in name_lower for kw in ["rule", "policy", "constraint"]):
        return "BusinessRule"

    # 基于 class_type
    class_type = class_data.get("class_type", "")
    if class_type == "abstract_class":
        return "AbstractEntity"

    return "Entity"


def _convert_ontology_to_visualization(
    ontology_data: Dict[str, Any],
    max_nodes: int = 500
) -> OntologyVisualizationResponse:
    """
    将后端 V3 本体格式转换为前端可视化格式

    Args:
        ontology_data: 原始本体 JSON 数据
        max_nodes: 最大节点数限制

    Returns:
        OntologyVisualizationResponse
    """
    nodes: List[OntologyNode] = []
    relations: List[OntologyRelation] = []
    relation_id_counter = 0

    meta = ontology_data.get("meta", {})
    schema = ontology_data.get("schema", {})
    business_logic = ontology_data.get("business_logic", {})

    classes = schema.get("classes", {})

    # 1. 首先添加域节点
    domains = meta.get("domains", [])
    for domain_name in domains:
        if len(nodes) >= max_nodes:
            break
        nodes.append(OntologyNode(
            id=f"domain_{domain_name}",
            label=_format_domain_label(domain_name),
            type="Domain",
            domain=domain_name,
            properties={
                "description": f"业务域：{_format_domain_label(domain_name)}",
            }
        ))

    # 2. 添加类/实体节点
    for domain_name, domain_classes in classes.items():
        if not isinstance(domain_classes, dict):
            continue

        for class_name, class_data in domain_classes.items():
            if len(nodes) >= max_nodes:
                break
            if not isinstance(class_data, dict):
                continue

            # 计算属性数量
            attributes = class_data.get("attributes", {})
            attribute_count = len(attributes) if isinstance(attributes, dict) else 0

            node_type = _determine_node_type(class_data, class_name)

            nodes.append(OntologyNode(
                id=class_name,
                label=_format_class_label(class_name, class_data),
                type=node_type,
                domain=domain_name,
                properties={
                    "description": class_data.get("description", ""),
                    "importance": class_data.get("importance", "medium"),
                    "class_type": class_data.get("class_type", "concrete_class"),
                    "attribute_count": attribute_count,
                    "lifecycle_states": class_data.get("lifecycle_states", []),
                    "why": class_data.get("why", ""),
                }
            ))

            # 3. 从 relations 字段提取关系
            class_relations = class_data.get("relations", {})
            if isinstance(class_relations, dict):
                # has_one 关系
                has_one = class_relations.get("has_one") or []
                if isinstance(has_one, str):
                    has_one = [has_one]
                for target in has_one:
                    relation_id_counter += 1
                    relations.append(OntologyRelation(
                        id=f"rel_{relation_id_counter}",
                        source=class_name,
                        target=target,
                        type="HAS_ONE",
                        properties={"domain": domain_name}
                    ))

                # has_many 关系
                has_many = class_relations.get("has_many") or []
                if isinstance(has_many, str):
                    has_many = [has_many]
                for target in has_many:
                    relation_id_counter += 1
                    relations.append(OntologyRelation(
                        id=f"rel_{relation_id_counter}",
                        source=class_name,
                        target=target,
                        type="HAS_MANY",
                        properties={"domain": domain_name}
                    ))

                # belongs_to 关系
                belongs_to = class_relations.get("belongs_to") or []
                if isinstance(belongs_to, str):
                    belongs_to = [belongs_to]
                for target in belongs_to:
                    relation_id_counter += 1
                    relations.append(OntologyRelation(
                        id=f"rel_{relation_id_counter}",
                        source=class_name,
                        target=target,
                        type="BELONGS_TO",
                        properties={"domain": domain_name}
                    ))

            # 4. 添加域到类的关系
            relation_id_counter += 1
            relations.append(OntologyRelation(
                id=f"rel_{relation_id_counter}",
                source=f"domain_{domain_name}",
                target=class_name,
                type="CONTAINS",
                properties={}
            ))

    # 5. 添加业务规则节点
    rules = business_logic.get("rules", {})
    for rule_name, rule_data in rules.items():
        if len(nodes) >= max_nodes:
            break
        if not isinstance(rule_data, dict):
            continue

        nodes.append(OntologyNode(
            id=rule_name,
            label=rule_data.get("name", rule_name),
            type="BusinessRule",
            properties={
                "description": rule_data.get("name", ""),
                "rule_type": rule_data.get("type", ""),
                "conditions": rule_data.get("conditions", []),
                "action": rule_data.get("action", ""),
                "confidence": rule_data.get("confidence", ""),
                "why": rule_data.get("why", ""),
            }
        ))

        # 业务规则应用到实体的关系
        applies_to = rule_data.get("applies_to", [])
        if isinstance(applies_to, str):
            applies_to = [applies_to]
        for entity in applies_to:
            relation_id_counter += 1
            relations.append(OntologyRelation(
                id=f"rel_{relation_id_counter}",
                source=rule_name,
                target=entity,
                type="APPLIES_TO",
                properties={}
            ))

    # 6. 添加指标节点
    metrics = business_logic.get("metrics", {})
    for metric_name, metric_data in metrics.items():
        if len(nodes) >= max_nodes:
            break
        if not isinstance(metric_data, dict):
            continue

        calculation = metric_data.get("calculation", {})
        formula = calculation.get("formula", "") if isinstance(calculation, dict) else ""

        nodes.append(OntologyNode(
            id=f"metric_{metric_name}",
            label=metric_data.get("description", metric_name),
            type="Metric",
            properties={
                "description": metric_data.get("definition", ""),
                "formula": formula,
                "why": metric_data.get("why", ""),
            }
        ))

    # 计算统计信息
    node_type_counts = {}
    for node in nodes:
        node_type_counts[node.type] = node_type_counts.get(node.type, 0) + 1

    statistics = {
        "total_nodes": len(nodes),
        "total_relations": len(relations),
        "domain_count": len(domains),
        "class_count": sum(
            len(domain_classes) if isinstance(domain_classes, dict) else 0
            for domain_classes in classes.values()
        ),
        "rule_count": len(rules),
        "metric_count": len(metrics),
        **node_type_counts
    }

    return OntologyVisualizationResponse(
        nodes=nodes,
        relations=relations,
        meta={
            "ontology_name": meta.get("ontology_name", ""),
            "product_name": meta.get("product_name", ""),
            "business_model": meta.get("business_model", ""),
            "created_at": meta.get("created_at", ""),
            "source_connection": meta.get("source_connection", ""),
            "version": ontology_data.get("version", ""),
        },
        statistics=statistics
    )


def _format_domain_label(domain_name: str) -> str:
    """格式化域名称为显示标签"""
    # 将 snake_case 转换为更友好的格式
    domain_labels = {
        "user_management": "用户管理",
        "order_payment": "订单支付",
        "ai_agent_management": "AI Agent 管理",
        "conversation_task": "对话任务",
        "billing_analytics": "计费分析",
        "operations_marketing": "运营营销",
    }
    return domain_labels.get(domain_name, domain_name.replace("_", " ").title())


def _format_class_label(class_name: str, class_data: Dict[str, Any]) -> str:
    """格式化类名称为显示标签"""
    # 优先使用 description 中的中文名
    description = class_data.get("description", "")
    if description:
        # 提取 【xxx】 中的产品名或前面的简短描述
        if "】" in description:
            parts = description.split("】", 1)
            if len(parts) > 1:
                short_desc = parts[1].strip()
                # 取第一个逗号前的内容
                if "，" in short_desc:
                    return short_desc.split("，")[0]
                if "," in short_desc:
                    return short_desc.split(",")[0]
                # 限制长度
                if len(short_desc) <= 20:
                    return short_desc

    # 回退到类名格式化
    return class_name.replace("_", " ").title()


async def _load_ontology_from_file(
    user_id: str,
    connection_name: str
) -> Optional[Dict[str, Any]]:
    """
    从文件加载本体数据

    Args:
        user_id: 用户 ID
        connection_name: 数据库连接名

    Returns:
        本体 JSON 数据，如果不存在返回 None
    """
    config = ConfigManager()
    ontology_path = config.get("storage.ontology_path", "./ontology_store")

    safe_conn_name = get_safe_connection_path(connection_name)
    ontology_file = Path(ontology_path) / user_id / safe_conn_name / "ontology.json"

    if not ontology_file.exists():
        logger.warning(f"Ontology file not found: {ontology_file}")
        return None

    try:
        with open(ontology_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load ontology file: {e}")
        return None


# ============ API Endpoints ============


@router.get(
    "/{project_id}/ontology/visualization",
    response_model=OntologyVisualizationResponse,
    responses={
        404: {"model": OntologyVisualizationError, "description": "本体不存在"},
        500: {"model": OntologyVisualizationError, "description": "服务器错误"},
    }
)
async def get_ontology_visualization(
    project_id: str,
    max_nodes: int = Query(500, ge=10, le=2000, description="最大返回节点数"),
    include_rules: bool = Query(True, description="是否包含业务规则"),
    include_metrics: bool = Query(True, description="是否包含业务指标"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    获取项目本体的可视化数据

    将后端存储的本体数据转换为前端可视化所需的节点和关系格式。

    Args:
        project_id: 项目 ID
        max_nodes: 最大节点数限制（默认 500，最大 2000）
        include_rules: 是否包含业务规则节点
        include_metrics: 是否包含业务指标节点
        current_user: 当前认证用户
        session: 数据库会话

    Returns:
        OntologyVisualizationResponse: 包含 nodes 和 relations 的可视化数据

    Raises:
        404: 项目或本体不存在
        500: 服务器内部错误
    """
    try:
        # 1. 验证项目存在且属于当前用户
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在或不属于当前用户"
            )

        # 2. 尝试从 ProjectOntology 获取本体数据
        result = await session.execute(
            select(ProjectOntology).where(ProjectOntology.project_id == project_id)
        )
        project_ontology = result.scalar_one_or_none()

        ontology_data = None

        if project_ontology and project_ontology.ontology_data:
            # 从数据库加载
            ontology_data = project_ontology.ontology_data
            logger.info(f"Loaded ontology from database for project {project_id}")
        else:
            # 3. 尝试从关联的数据源加载本体文件
            # 获取项目关联的已融合数据源
            result = await session.execute(
                select(ProjectDataSource, DataSource)
                .join(DataSource, ProjectDataSource.data_source_id == DataSource.id)
                .where(
                    ProjectDataSource.project_id == project_id,
                    ProjectDataSource.status == ProjectDataSourceStatus.MERGED
                )
            )
            associations = result.all()

            if associations:
                # 使用第一个已融合的数据源
                _, data_source = associations[0]
                connection_name = data_source.name

                ontology_data = await _load_ontology_from_file(
                    current_user.id,
                    connection_name
                )

                if ontology_data:
                    logger.info(
                        f"Loaded ontology from file for connection {connection_name}"
                    )

        if not ontology_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目尚未构建本体，请先关联数据源并构建本体"
            )

        # 4. 转换为可视化格式
        visualization = _convert_ontology_to_visualization(
            ontology_data,
            max_nodes=max_nodes
        )

        # 5. 根据参数过滤节点
        if not include_rules:
            visualization.nodes = [
                n for n in visualization.nodes if n.type != "BusinessRule"
            ]
            visualization.relations = [
                r for r in visualization.relations if r.type != "APPLIES_TO"
            ]

        if not include_metrics:
            visualization.nodes = [
                n for n in visualization.nodes if n.type != "Metric"
            ]

        # 重新计算统计
        if not include_rules or not include_metrics:
            visualization.statistics["total_nodes"] = len(visualization.nodes)
            visualization.statistics["total_relations"] = len(visualization.relations)

        return visualization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取本体可视化数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取本体可视化数据失败: {str(e)}"
        )


@router.get(
    "/{project_id}/ontology/visualization/by-connection/{connection_name}",
    response_model=OntologyVisualizationResponse,
    responses={
        404: {"model": OntologyVisualizationError, "description": "本体不存在"},
        500: {"model": OntologyVisualizationError, "description": "服务器错误"},
    }
)
async def get_ontology_visualization_by_connection(
    project_id: str,
    connection_name: str,
    max_nodes: int = Query(500, ge=10, le=2000, description="最大返回节点数"),
    include_rules: bool = Query(True, description="是否包含业务规则"),
    include_metrics: bool = Query(True, description="是否包含业务指标"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    根据数据库连接名获取本体可视化数据

    直接从 ontology_store/{user_id}/{connection_name}/ontology.json 加载。

    Args:
        project_id: 项目 ID（用于权限验证）
        connection_name: 数据库连接名
        max_nodes: 最大节点数限制
        include_rules: 是否包含业务规则节点
        include_metrics: 是否包含业务指标节点
        current_user: 当前认证用户
        session: 数据库会话

    Returns:
        OntologyVisualizationResponse
    """
    try:
        # 验证项目存在且属于当前用户
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在或不属于当前用户"
            )

        # 从文件加载本体
        ontology_data = await _load_ontology_from_file(
            current_user.id,
            connection_name
        )

        if not ontology_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到连接 '{connection_name}' 的本体数据"
            )

        # 转换为可视化格式
        visualization = _convert_ontology_to_visualization(
            ontology_data,
            max_nodes=max_nodes
        )

        # 根据参数过滤节点
        if not include_rules:
            visualization.nodes = [
                n for n in visualization.nodes if n.type != "BusinessRule"
            ]
            visualization.relations = [
                r for r in visualization.relations if r.type != "APPLIES_TO"
            ]

        if not include_metrics:
            visualization.nodes = [
                n for n in visualization.nodes if n.type != "Metric"
            ]

        # 重新计算统计
        if not include_rules or not include_metrics:
            visualization.statistics["total_nodes"] = len(visualization.nodes)
            visualization.statistics["total_relations"] = len(visualization.relations)

        return visualization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取本体可视化数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取本体可视化数据失败: {str(e)}"
        )


@router.get(
    "/{project_id}/ontology/visualization/domains",
    response_model=List[Dict[str, Any]],
)
async def get_ontology_domains(
    project_id: str,
    connection_name: Optional[str] = Query(None, description="数据库连接名"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    获取本体的域列表

    返回本体中所有业务域的概要信息，用于前端筛选。

    Args:
        project_id: 项目 ID
        connection_name: 可选的数据库连接名
        current_user: 当前认证用户
        session: 数据库会话

    Returns:
        域列表，每个域包含名称、标签和类数量
    """
    try:
        # 验证项目存在且属于当前用户
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在"
            )

        ontology_data = None

        # 如果指定了 connection_name，从文件加载
        if connection_name:
            ontology_data = await _load_ontology_from_file(
                current_user.id,
                connection_name
            )
        else:
            # 从 ProjectOntology 加载
            result = await session.execute(
                select(ProjectOntology).where(ProjectOntology.project_id == project_id)
            )
            project_ontology = result.scalar_one_or_none()

            if project_ontology and project_ontology.ontology_data:
                ontology_data = project_ontology.ontology_data

        if not ontology_data:
            return []

        # 提取域信息
        meta = ontology_data.get("meta", {})
        schema = ontology_data.get("schema", {})
        classes = schema.get("classes", {})

        domains = []
        for domain_name in meta.get("domains", []):
            domain_classes = classes.get(domain_name, {})
            class_count = len(domain_classes) if isinstance(domain_classes, dict) else 0

            domains.append({
                "id": f"domain_{domain_name}",
                "name": domain_name,
                "label": _format_domain_label(domain_name),
                "class_count": class_count,
            })

        return domains

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取本体域列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取本体域列表失败: {str(e)}"
        )
