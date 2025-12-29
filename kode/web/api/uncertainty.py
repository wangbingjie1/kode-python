"""
Uncertainty Management API Routes

REST endpoints for managing uncertainty Q&A workflow.
"""

import asyncio
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pathlib import Path
import json
from typing import Dict, Any, Optional

from kode.schemas.uncertainty import (
    LoadUncertaintiesRequest,
    LoadUncertaintiesResponse,
    BatchAnswerRequest,
    BatchAnswerResponse,
    UncertaintyStatusResponse,
    UncertaintyGroupByDomain,
    UncertaintyItem,
    # 新增：侧边栏问卷 API
    SidebarLoadRequest,
    SidebarLoadResponse,
    SingleAnswerRequest,
    SingleAnswerResponse,
    SidebarBatchAnswerRequest,
    SidebarBatchAnswerResponse,
    SkipQuestionRequest,
    SkipQuestionResponse,
    # 新增：AI 分析 API
    AcceptAIAnswerRequest,
    AcceptAIAnswerResponse,
)
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger
from kode.utils.context import get_current_user_id
from kode.utils.path_utils import get_safe_connection_path
from datetime import datetime

logger = setup_logger(__name__)
router = APIRouter()


def _get_ontology_file(connection_name: str, user_id: str = None) -> Path:
    """获取本体文件路径（优先 v3，回退到 v2，再回退到 business_context）

    Args:
        connection_name: 数据库连接名
        user_id: 用户 ID（如果为 None，则自动获取当前用户）

    Returns:
        本体文件的 Path 对象
    """
    config = ConfigManager()
    ontology_path = config.get("storage.ontology_path", "./ontology_store")

    # 获取用户 ID（支持用户隔离）
    if user_id is None:
        user_id = get_current_user_id()

    # 构建用户隔离路径：ontology_store/{user_id}/{connection_name}/
    safe_conn_name = get_safe_connection_path(connection_name)
    base_path = Path(ontology_path) / user_id / safe_conn_name

    # 优先使用 v3 版本
    v3_file = base_path / "ontology_v3.json"
    if v3_file.exists():
        return v3_file

    # 回退到 v2 版本
    v2_file = base_path / "ontology_v2.json"
    if v2_file.exists():
        return v2_file

    # 再回退到 business_context.json（业务理解问卷结果）
    return base_path / "business_context.json"


def _get_domains_dir(connection_name: str, user_id: str = None) -> Path:
    """获取领域不确定性分析目录

    Args:
        connection_name: 数据库连接名
        user_id: 用户 ID（如果为 None，则自动获取当前用户）

    Returns:
        领域目录的 Path 对象
    """
    config = ConfigManager()
    # 🔧 修复：领域文件存储在 schema_store 而不是 ontology_store
    schema_path = config.get("storage.schema_path", "./schema_store")

    # 获取用户 ID
    if user_id is None:
        user_id = get_current_user_id()

    # 构建路径：schema_store/{user_id}/{connection_name}/domains/
    safe_conn_name = get_safe_connection_path(connection_name)
    return Path(schema_path) / user_id / safe_conn_name / "domains"


def _load_ontology(ontology_file: Path) -> Dict[str, Any]:
    """加载本体文件"""
    if not ontology_file.exists():
        return None
    with open(ontology_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_all_domain_files(domains_dir: Path) -> list:
    """加载指定目录下所有领域分析文件

    Args:
        domains_dir: 领域文件目录

    Returns:
        领域数据列表
    """
    domain_data_list = []
    if not domains_dir.exists():
        return domain_data_list

    for domain_file in domains_dir.glob("*.json"):
        try:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)
                domain_data["_file_path"] = str(domain_file)
                domain_data_list.append(domain_data)
        except Exception as e:
            logger.warning(f"Failed to load domain file {domain_file}: {e}")
            continue

    return domain_data_list


@router.post("/load", response_model=LoadUncertaintiesResponse)
async def load_uncertainties(request: LoadUncertaintiesRequest):
    """
    批量加载不确定性问题（高优先级）

    Args:
        request: 加载请求（包含连接名、分组方式、限制数量）

    Returns:
        LoadUncertaintiesResponse: 分组后的问题列表
    """
    try:
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domains directory not found. Run DomainUncertaintyAnalyzer first."
            )

        # 🔥 从各个领域文件加载不确定性
        domain_data_list = _load_all_domain_files(domains_dir)

        # 收集所有未解决的高优先级问题
        high_uncertainties = []
        for domain_data in domain_data_list:
            domain_name = domain_data.get("domain_name", Path(domain_data["_file_path"]).stem)
            for u in domain_data.get("uncertainties", []):
                if u.get("priority", "medium").lower() == "high" and u.get("status") not in ["resolved", "skipped"]:
                    u["domain"] = domain_name
                    high_uncertainties.append(u)

        # 为每个问题生成唯一 ID
        for idx, u in enumerate(high_uncertainties):
            if "id" not in u:
                u["id"] = f"{u.get('domain')}_{u.get('entity')}_{idx}"

        # 应用 limit
        if request.limit and request.limit > 0:
            high_uncertainties = high_uncertainties[:request.limit]

        # 分组
        if request.group_by == "domain":
            groups_dict: Dict[str, list] = {}
            for u in high_uncertainties:
                domain = u.get("domain", "unknown")
                if domain not in groups_dict:
                    groups_dict[domain] = []
                groups_dict[domain].append(UncertaintyItem(**u))

            groups = [
                UncertaintyGroupByDomain(
                    domain=domain,
                    question_count=len(questions),
                    questions=questions
                )
                for domain, questions in groups_dict.items()
            ]
        else:
            # 不分组或按优先级分组，都返回单个组
            questions = [UncertaintyItem(**u) for u in high_uncertainties]
            groups = [
                UncertaintyGroupByDomain(
                    domain="all",
                    question_count=len(questions),
                    questions=questions
                )
            ]

        return LoadUncertaintiesResponse(
            status="success",
            connection_name=request.connection_name,
            total_loaded=len(high_uncertainties),
            group_by=request.group_by,
            groups=groups,
            message=f"已加载 {len(high_uncertainties)} 个高优先级问题，按 {request.group_by} 分组展示。"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load uncertainties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load uncertainties: {str(e)}"
        )


@router.post("/batch-answer", response_model=BatchAnswerResponse)
async def batch_answer_uncertainties(request: BatchAnswerRequest):
    """
    批量回答不确定性问题（已废弃，现在通过 SSE 的 UserInputRequired 机制处理）

    ⚠️ 此端点保留是为了向后兼容，但新流程不再使用它。
    新流程：batch_load → UserInputRequired → 前端提交 → SSE user-response 端点

    Args:
        request: 批量回答请求

    Returns:
        BatchAnswerResponse: 批量回答结果
    """
    logger.warning("[batch-answer] This endpoint is deprecated, use SSE user-response instead")

    # 简单返回成功，实际逻辑已迁移到 UncertaintyQAManager._wait_for_response
    return BatchAnswerResponse(
        status="deprecated",
        resolved_count=0,
        not_found=[],
        remaining_high_priority=0,
        can_build_ontology=False,
        message="此端点已废弃，请使用 SSE 的 UserInputRequired 机制"
    )


@router.get("/status/{connection_name}", response_model=UncertaintyStatusResponse)
async def get_uncertainty_status(connection_name: str):
    """
    获取不确定性问答状态

    Args:
        connection_name: 数据库连接名称

    Returns:
        UncertaintyStatusResponse: 问答状态统计
    """
    try:
        domains_dir = _get_domains_dir(connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domains directory not found. Run DomainUncertaintyAnalyzer first."
            )

        # 🔥 从所有领域文件收集不确定性
        all_uncertainties = []
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)
            all_uncertainties.extend(domain_data.get("uncertainties", []))

        # 统计各优先级的解决情况
        summary = {}
        for priority in ["high", "medium", "low"]:
            uncertainties = [u for u in all_uncertainties if u.get("priority", "medium").lower() == priority]
            total = len(uncertainties)
            resolved = len([u for u in uncertainties if u.get("status") == "resolved"])
            skipped = len([u for u in uncertainties if u.get("status") == "skipped"])
            summary[priority] = {
                "total": total,
                "resolved": resolved,
                "skipped": skipped,
                "remaining": total - resolved - skipped
            }

        can_build = summary["high"]["remaining"] == 0

        return UncertaintyStatusResponse(
            status="success",
            connection_name=connection_name,
            summary=summary,
            can_build_ontology=can_build,
            message=(
                "所有高优先级问题已解决，可以构建本体！"
                if can_build
                else f"还有 {summary['high']['remaining']} 个高优先级问题待解决，必须先回答这些问题。"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get uncertainty status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get uncertainty status: {str(e)}"
        )


# ============== 新增：侧边栏问卷 API ==============


def _compute_summary(all_uncertainties: list) -> Dict[str, Dict[str, int]]:
    """计算各优先级统计"""
    summary = {}
    for priority in ["high", "medium", "low"]:
        uncertainties = [u for u in all_uncertainties if u.get("priority", "medium").lower() == priority]
        total = len(uncertainties)
        resolved = len([u for u in uncertainties if u.get("status") == "resolved"])
        skipped = len([u for u in uncertainties if u.get("status") == "skipped"])
        summary[priority] = {
            "total": total,
            "resolved": resolved,
            "skipped": skipped,
            "remaining": total - resolved - skipped
        }
    return summary


def _save_ontology(ontology_file: Path, ontology_data: Dict[str, Any]):
    """保存本体文件"""
    with open(ontology_file, "w", encoding="utf-8") as f:
        json.dump(ontology_data, f, indent=2, ensure_ascii=False)


@router.post("/sidebar/load", response_model=SidebarLoadResponse)
async def sidebar_load_uncertainties(request: SidebarLoadRequest):
    """
    侧边栏加载不确定性问题（支持更灵活的过滤）

    前端侧边栏在用户选择数据库后调用此 API 加载问卷。
    支持按优先级、状态过滤，支持分页。

    Args:
        request: 加载请求

    Returns:
        SidebarLoadResponse: 分组后的问题列表和统计信息
    """
    try:
        all_uncertainties = []
        data_source = None  # 记录数据来源：'ontology' 或 'domains'

        # 🔧 优先从本体文件加载，如果不存在则回退到领域文件
        ontology_file = _get_ontology_file(request.connection_name)
        domains_dir = _get_domains_dir(request.connection_name)

        if ontology_file.exists():
            # 加载本体文件
            ontology_data = _load_ontology(ontology_file)
            if ontology_data:
                all_uncertainties = ontology_data.get("uncertainties", [])
                data_source = 'ontology'

                # 检查是否是 business_context.json（业务理解问卷结果，没有 uncertainties）
                is_business_context_only = (
                    ("answers" in ontology_data or "qa_pairs" in ontology_data) and
                    "entities" not in ontology_data and
                    len(all_uncertainties) == 0
                )

                if is_business_context_only:
                    # 回退到领域文件
                    data_source = None

        # 如果本体文件没有不确定性数据，尝试从领域文件加载
        if not all_uncertainties and domains_dir.exists():
            domain_data_list = _load_all_domain_files(domains_dir)
            for domain_data in domain_data_list:
                domain_name = domain_data.get("domain_name", Path(domain_data.get("_file_path", "unknown")).stem)
                for u in domain_data.get("uncertainties", []):
                    u["domain"] = domain_name
                    all_uncertainties.append(u)
            if all_uncertainties:
                data_source = 'domains'

        # 如果仍然没有数据
        if not all_uncertainties:
            return SidebarLoadResponse(
                status="no_analysis",
                connection_name=request.connection_name,
                total_count=0,
                filtered_count=0,
                groups=[],
                summary={"high": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0},
                         "medium": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0},
                         "low": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0}},
                can_build_ontology=False,
                message="尚未进行不确定性分析，请先让 AI 分析数据库结构。"
            )

        # 计算总统计
        summary = _compute_summary(all_uncertainties)
        total_count = len(all_uncertainties)

        # 应用过滤
        filtered = all_uncertainties
        logger.info(f"[sidebar/load] all_uncertainties={len(all_uncertainties)}, priority_filter={request.priority_filter}, status_filter={request.status_filter}")

        # 优先级过滤
        if request.priority_filter:
            filtered = [u for u in filtered if u.get("priority", "medium").lower() in request.priority_filter]
            logger.info(f"[sidebar/load] after priority filter: {len(filtered)}")

        # 状态过滤
        # - 如果 status_filter 为 None 或空列表，不过滤（返回所有状态）
        # - 如果包含 "pending"，匹配 status 为空或不在 resolved/skipped 中的
        # - 如果包含 "resolved"/"skipped"，匹配对应状态
        if request.status_filter:
            logger.info(f"[sidebar/load] applying status filter: {request.status_filter}")
            def match_status(u):
                status = u.get("status")
                # pending 匹配：status 为空或不在 resolved/skipped 中
                if "pending" in request.status_filter:
                    if status not in ["resolved", "skipped"]:
                        return True
                # resolved/skipped 直接匹配
                if status in request.status_filter:
                    return True
                return False
            filtered = [u for u in filtered if match_status(u)]
            logger.info(f"[sidebar/load] after status filter: {len(filtered)}")
        else:
            logger.info(f"[sidebar/load] NO status filter applied, keeping {len(filtered)} items")

        # 为没有 ID 的问题生成 ID
        for idx, u in enumerate(filtered):
            if "id" not in u:
                u["id"] = f"{u.get('domain')}_{u.get('entity')}_{idx}"

        # 应用 limit
        if request.limit and request.limit > 0:
            filtered = filtered[:request.limit]

        # 分组
        if request.group_by == "domain":
            groups_dict: Dict[str, list] = {}
            for u in filtered:
                domain = u.get("domain", "unknown")
                if domain not in groups_dict:
                    groups_dict[domain] = []
                groups_dict[domain].append(UncertaintyItem(**u))

            groups = [
                UncertaintyGroupByDomain(
                    domain=domain,
                    question_count=len(questions),
                    questions=questions
                )
                for domain, questions in groups_dict.items()
            ]
        elif request.group_by == "priority":
            groups_dict: Dict[str, list] = {}
            for u in filtered:
                priority = u.get("priority", "medium")
                if priority not in groups_dict:
                    groups_dict[priority] = []
                groups_dict[priority].append(UncertaintyItem(**u))

            # 按优先级排序：high > medium > low
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_items = sorted(groups_dict.items(), key=lambda x: priority_order.get(x[0], 99))
            groups = [
                UncertaintyGroupByDomain(
                    domain=priority,  # 这里 domain 字段复用为 priority
                    question_count=len(questions),
                    questions=questions
                )
                for priority, questions in sorted_items
            ]
        else:
            # 不分组
            questions = [UncertaintyItem(**u) for u in filtered]
            groups = [
                UncertaintyGroupByDomain(
                    domain="all",
                    question_count=len(questions),
                    questions=questions
                )
            ] if questions else []

        can_build = summary["high"]["remaining"] == 0

        return SidebarLoadResponse(
            status="success",
            connection_name=request.connection_name,
            total_count=total_count,
            filtered_count=len(filtered),
            groups=groups,
            summary=summary,
            can_build_ontology=can_build,
            message=f"共 {total_count} 个问题，显示 {len(filtered)} 个" +
                    ("，可以构建本体" if can_build else f"，还需回答 {summary['high']['remaining']} 个高优先级问题")
        )

    except Exception as e:
        logger.error(f"Failed to load sidebar uncertainties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载问卷失败: {str(e)}"
        )


@router.post("/sidebar/answer", response_model=SingleAnswerResponse)
async def sidebar_answer_single(request: SingleAnswerRequest):
    """
    回答单个不确定性问题

    前端侧边栏中用户回答单个问题后调用。
    答案会保存到本体文件或领域文件。

    Args:
        request: 单个回答请求

    Returns:
        SingleAnswerResponse: 回答结果和剩余问题统计
    """
    try:
        # 🔧 优先从本体文件查找，如果不存在则查找领域文件
        ontology_file = _get_ontology_file(request.connection_name)
        domains_dir = _get_domains_dir(request.connection_name)

        ontology_data = None
        domain_file_path = None  # 记录找到问题的领域文件路径
        data_source = None

        # 先尝试本体文件
        if ontology_file.exists():
            ontology_data = _load_ontology(ontology_file)
            if ontology_data and ontology_data.get("uncertainties"):
                data_source = 'ontology'

        # 如果本体文件没有不确定性，尝试领域文件
        if not data_source and domains_dir.exists():
            for domain_file in domains_dir.glob("*.json"):
                try:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        domain_data = json.load(f)
                    for u in domain_data.get("uncertainties", []):
                        if u.get("id") == request.uncertainty_id:
                            ontology_data = domain_data
                            domain_file_path = domain_file
                            data_source = 'domains'
                            break
                    if data_source:
                        break
                except Exception:
                    continue

        if not ontology_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到本体文件或领域文件"
            )

        # 查找并更新问题
        found = False
        uncertainties = ontology_data.get("uncertainties", [])

        for u in uncertainties:
            if u.get("id") == request.uncertainty_id:
                u["status"] = "resolved"
                u["answer"] = request.answer
                u["answered_at"] = datetime.now().isoformat()
                found = True
                logger.info(f"[sidebar/answer] Updated uncertainty {request.uncertainty_id}: {request.answer}")
                break

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到问题 ID: {request.uncertainty_id}"
            )

        # 🔧 根据数据来源保存到正确的文件
        if data_source == 'domains' and domain_file_path:
            with open(domain_file_path, "w", encoding="utf-8") as f:
                json.dump(ontology_data, f, indent=2, ensure_ascii=False)
            logger.info(f"[sidebar/answer] Saved to domain file: {domain_file_path}")
        else:
            _save_ontology(ontology_file, ontology_data)

        # ========== 新增：自动更新本体实体描述 ==========
        try:
            from kode.services.ontology_updater import OntologyDescriptionUpdater
            from kode.core.model_manager import ModelManager
            from kode.utils.config import ConfigManager

            # 获取已回答的不确定性对象
            target_uncertainty = None
            for u in uncertainties:
                if u.get("id") == request.uncertainty_id:
                    target_uncertainty = u
                    break

            if target_uncertainty:
                # 创建 ModelManager 实例
                config_manager = ConfigManager()
                config = config_manager.get_all()
                model_manager = ModelManager(config)

                updater = OntologyDescriptionUpdater(model_manager)
                update_result = await updater.update_from_answer(
                    connection_name=request.connection_name,
                    uncertainty=target_uncertainty,
                    answer=request.answer,
                    conversation_id=None
                )

                if update_result.get("status") == "success":
                    logger.info(
                        f"✅ 本体描述已自动更新: {update_result.get('entity')} "
                        f"({update_result.get('level')})"
                    )
                elif update_result.get("status") == "skip":
                    logger.info(
                        f"⏭️ 本体更新跳过: {update_result.get('message')}"
                    )
                else:
                    logger.warning(
                        f"⚠️ 本体更新失败: {update_result.get('message')}"
                    )
        except Exception as e:
            logger.error(f"❌ 自动更新本体异常（已忽略）: {e}", exc_info=True)
        # ================================================

        # 计算剩余高优先级问题
        # 🔧 如果是从领域文件加载，需要从所有领域文件汇总统计
        if data_source == 'domains':
            all_uncertainties = []
            for domain_file in domains_dir.glob("*.json"):
                try:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        domain_data = json.load(f)
                    all_uncertainties.extend(domain_data.get("uncertainties", []))
                except Exception:
                    continue
            summary = _compute_summary(all_uncertainties)
        else:
            summary = _compute_summary(uncertainties)
        can_build = summary["high"]["remaining"] == 0

        return SingleAnswerResponse(
            status="success",
            uncertainty_id=request.uncertainty_id,
            message="回答已保存",
            remaining_high_priority=summary["high"]["remaining"],
            can_build_ontology=can_build
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save answer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存回答失败: {str(e)}"
        )


@router.post("/sidebar/batch-answer", response_model=SidebarBatchAnswerResponse)
async def sidebar_batch_answer(request: SidebarBatchAnswerRequest):
    """
    批量回答不确定性问题（独立 API，不走 SSE 流程）

    前端侧边栏中用户批量提交答案时调用。
    与 SSE 的 UserInputRequired 机制无关，是完全独立的 REST API。

    Args:
        request: 批量回答请求

    Returns:
        SidebarBatchAnswerResponse: 批量回答结果
    """
    try:
        # 🔧 优先从本体文件查找，如果不存在则查找领域文件
        ontology_file = _get_ontology_file(request.connection_name)
        domains_dir = _get_domains_dir(request.connection_name)

        data_source = None
        domain_files_data = {}  # {file_path: data} 用于批量更新领域文件

        # 先尝试本体文件
        if ontology_file.exists():
            ontology_data = _load_ontology(ontology_file)
            if ontology_data and ontology_data.get("uncertainties"):
                data_source = 'ontology'

        # 如果本体文件没有不确定性，尝试领域文件
        if not data_source and domains_dir.exists():
            for domain_file in domains_dir.glob("*.json"):
                try:
                    with open(domain_file, "r", encoding="utf-8") as f:
                        domain_data = json.load(f)
                    if domain_data.get("uncertainties"):
                        domain_files_data[domain_file] = domain_data
                except Exception:
                    continue
            if domain_files_data:
                data_source = 'domains'

        if not data_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到本体文件或领域文件"
            )

        resolved_count = 0
        not_found = list(request.answers.keys())

        if data_source == 'ontology':
            uncertainties = ontology_data.get("uncertainties", [])
            # 更新所有匹配的问题
            for u in uncertainties:
                uncertainty_id = u.get("id")
                if uncertainty_id in request.answers:
                    answer = request.answers[uncertainty_id]
                    u["status"] = "resolved"
                    u["answer"] = answer
                    u["answered_at"] = datetime.now().isoformat()
                    resolved_count += 1
                    not_found.remove(uncertainty_id)
                    logger.info(f"[sidebar/batch-answer] Updated {uncertainty_id}: {answer}")
            # 保存本体文件
            _save_ontology(ontology_file, ontology_data)
            summary = _compute_summary(uncertainties)
        else:
            # 从领域文件批量更新
            all_uncertainties = []
            for domain_file, domain_data in domain_files_data.items():
                updated = False
                for u in domain_data.get("uncertainties", []):
                    uncertainty_id = u.get("id")
                    if uncertainty_id in request.answers:
                        answer = request.answers[uncertainty_id]
                        u["status"] = "resolved"
                        u["answer"] = answer
                        u["answered_at"] = datetime.now().isoformat()
                        resolved_count += 1
                        if uncertainty_id in not_found:
                            not_found.remove(uncertainty_id)
                        updated = True
                        logger.info(f"[sidebar/batch-answer] Updated {uncertainty_id}: {answer}")
                    all_uncertainties.append(u)
                # 保存更新后的领域文件
                if updated:
                    with open(domain_file, "w", encoding="utf-8") as f:
                        json.dump(domain_data, f, indent=2, ensure_ascii=False)
            summary = _compute_summary(all_uncertainties)

        can_build = summary["high"]["remaining"] == 0

        return SidebarBatchAnswerResponse(
            status="success",
            resolved_count=resolved_count,
            not_found=not_found,
            remaining_high_priority=summary["high"]["remaining"],
            can_build_ontology=can_build,
            summary=summary,
            message=f"已保存 {resolved_count} 个回答" +
                    (f"，{len(not_found)} 个问题未找到" if not_found else "") +
                    ("，可以构建本体！" if can_build else f"，还需回答 {summary['high']['remaining']} 个高优先级问题")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch save answers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量保存回答失败: {str(e)}"
        )


@router.post("/sidebar/skip", response_model=SkipQuestionResponse)
async def sidebar_skip_question(request: SkipQuestionRequest):
    """
    跳过单个不确定性问题

    注意：高优先级问题不允许跳过（返回错误）。
    中/低优先级问题可以跳过。

    Args:
        request: 跳过请求

    Returns:
        SkipQuestionResponse: 跳过结果
    """
    try:
        ontology_file = _get_ontology_file(request.connection_name)

        if not ontology_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到本体文件"
            )

        # 加载本体文件
        ontology_data = _load_ontology(ontology_file)
        if not ontology_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="本体文件加载失败"
            )

        found = False
        found_priority = None
        uncertainties = ontology_data.get("uncertainties", [])

        for u in uncertainties:
            if u.get("id") == request.uncertainty_id:
                found = True
                found_priority = u.get("priority", "medium")

                # 高优先级不允许跳过
                if found_priority == "high":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="高优先级问题不允许跳过，必须回答！"
                    )

                u["status"] = "skipped"
                u["skip_reason"] = request.reason or "用户跳过"
                u["skipped_at"] = datetime.now().isoformat()
                logger.info(f"[sidebar/skip] Skipped {request.uncertainty_id}")
                break

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到问题 ID: {request.uncertainty_id}"
            )

        # 保存本体文件
        _save_ontology(ontology_file, ontology_data)

        # 计算统计
        summary = _compute_summary(uncertainties)
        can_build = summary["high"]["remaining"] == 0

        return SkipQuestionResponse(
            status="success",
            uncertainty_id=request.uncertainty_id,
            skipped_priority=found_priority,
            message=f"已跳过 {found_priority} 优先级问题",
            remaining_high_priority=summary["high"]["remaining"],
            can_build_ontology=can_build
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to skip question: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"跳过问题失败: {str(e)}"
        )


# ============== AI 分析 API ==============


@router.get("/sidebar/ai-analyze")
async def ai_analyze_uncertainties(
    request: Request,
    connection_name: str,
    priority_filter: Optional[str] = None,
    limit: int = 50,
):
    """
    AI 自动分析不确定性问题（SSE 流式响应）

    通过查询数据库数据来验证和解决不确定性问题。
    结果需要用户确认后才会保存到本体文件。

    SSE 事件类型:
    - start: 开始分析
    - progress: 进度更新
    - question_result: 单个问题分析结果
    - complete: 分析完成
    - error: 错误
    - cancelled: 用户取消

    Args:
        connection_name: 数据库连接名称
        priority_filter: 优先级过滤，逗号分隔，如 'high,medium'
        limit: 最大分析问题数，默认 50
    """
    # 🔥 重要：在创建生成器之前捕获 user_id
    # SSE 生成器在 middleware 清理上下文之后才执行，所以必须提前获取
    try:
        user_id = get_current_user_id()
    except RuntimeError:
        # 用户上下文未设置，返回错误
        logger.error("[AI分析] 无法获取用户上下文，需要登录")

        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'content': '用户未登录或会话已过期，请重新登录', 'metadata': {'error_type': 'auth_error'}})}\n\n"

        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_generator():
        try:
            # 延迟导入，避免循环依赖
            from kode.services.uncertainty_analyzer import UncertaintyAnalyzer, get_schema_context
            from kode.core.model_manager import ModelManager

            # 1. 加载本体文件（使用预先捕获的 user_id）
            ontology_file = _get_ontology_file(connection_name, user_id=user_id)
            if not ontology_file.exists():
                yield f"data: {json.dumps({'type': 'error', 'content': '未找到本体文件，请先构建本体', 'metadata': {'error_type': 'not_found'}})}\n\n"
                return

            ontology_data = _load_ontology(ontology_file)
            if not ontology_data:
                yield f"data: {json.dumps({'type': 'error', 'content': '本体文件加载失败', 'metadata': {'error_type': 'load_error'}})}\n\n"
                return

            uncertainties = ontology_data.get("uncertainties", [])
            if not uncertainties:
                yield f"data: {json.dumps({'type': 'error', 'content': '没有不确定性问题', 'metadata': {'error_type': 'no_questions'}})}\n\n"
                return

            # 2. 应用优先级过滤
            if priority_filter:
                priorities = [p.strip() for p in priority_filter.split(",")]
                uncertainties = [u for u in uncertainties if u.get("priority", "medium") in priorities]

            # 3. 只处理待解决的问题
            pending_uncertainties = [u for u in uncertainties if u.get("status") not in ["resolved", "skipped"]]

            # 4. 应用数量限制
            if limit and limit > 0:
                pending_uncertainties = pending_uncertainties[:limit]

            if not pending_uncertainties:
                yield f"data: {json.dumps({'type': 'complete', 'content': '没有待分析的问题', 'metadata': {'total_analyzed': 0, 'resolved_count': 0, 'partial_count': 0, 'failed_count': 0}})}\n\n"
                return

            # 5. 加载 schema 上下文（使用预先捕获的 user_id）
            schema_context = get_schema_context(connection_name, user_id=user_id)

            # 6. 创建分析器
            config_manager = ConfigManager()
            config = config_manager.get_all()
            model_manager = ModelManager(config)
            analyzer = UncertaintyAnalyzer(model_manager)

            # 7. 执行流式分析
            async for event in analyzer.analyze_uncertainties_stream(
                connection_name=connection_name,
                uncertainties=pending_uncertainties,
                schema_context=schema_context,
            ):
                # 检查客户端是否断开
                if await request.is_disconnected():
                    logger.info("[AI分析] 客户端断开连接")
                    break

                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

        except Exception as e:
            logger.error(f"AI 分析失败: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'分析失败: {str(e)}', 'metadata': {'error_type': 'internal'}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/sidebar/accept-ai-answer", response_model=AcceptAIAnswerResponse)
async def accept_ai_answer(request: AcceptAIAnswerRequest):
    """
    采纳 AI 分析答案

    将 AI 生成的答案写入本体文件。
    这个端点复用 sidebar_answer_single 的逻辑。

    Args:
        request: 采纳请求，包含问题 ID 和 AI 生成的答案

    Returns:
        AcceptAIAnswerResponse: 采纳结果
    """
    try:
        ontology_file = _get_ontology_file(request.connection_name)

        if not ontology_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到本体文件"
            )

        # 加载本体文件
        ontology_data = _load_ontology(ontology_file)
        if not ontology_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="本体文件加载失败"
            )

        # 查找并更新问题
        found = False
        uncertainties = ontology_data.get("uncertainties", [])

        for u in uncertainties:
            if u.get("id") == request.uncertainty_id:
                u["status"] = "resolved"
                u["answer"] = request.answer
                u["answered_at"] = datetime.now().isoformat()
                u["answer_source"] = "ai_analysis"  # 标记答案来源
                if request.confidence:
                    u["ai_confidence"] = request.confidence
                if request.reasoning:
                    u["ai_reasoning"] = request.reasoning
                found = True
                logger.info(f"[accept-ai-answer] 采纳 AI 答案: {request.uncertainty_id}")
                break

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到问题 ID: {request.uncertainty_id}"
            )

        # 保存本体文件
        _save_ontology(ontology_file, ontology_data)

        # 尝试更新本体实体描述（与 sidebar_answer_single 一致）
        try:
            from kode.services.ontology_updater import OntologyDescriptionUpdater
            from kode.core.model_manager import ModelManager

            target_uncertainty = None
            for u in uncertainties:
                if u.get("id") == request.uncertainty_id:
                    target_uncertainty = u
                    break

            if target_uncertainty:
                config_manager = ConfigManager()
                config = config_manager.get_all()
                model_manager = ModelManager(config)

                updater = OntologyDescriptionUpdater(model_manager)
                update_result = await updater.update_from_answer(
                    connection_name=request.connection_name,
                    uncertainty=target_uncertainty,
                    answer=request.answer,
                    conversation_id=None
                )

                if update_result.get("status") == "success":
                    logger.info(f"✅ 本体描述已自动更新: {update_result.get('entity')}")

                    # 强制同步写入磁盘，避免前端重新加载时文件还没写完
                    try:
                        from kode.tools.ontology_update.update_tool import OntologyUpdateTool
                        update_tool = OntologyUpdateTool()
                        update_tool.force_flush_all()
                        logger.info("✅ 本体变更已同步写入磁盘")
                    except Exception as flush_error:
                        logger.warning(f"⚠️ 强制刷新磁盘失败（不影响功能）: {flush_error}")
        except Exception as e:
            logger.error(f"❌ 自动更新本体异常（已忽略）: {e}")

        # 计算剩余高优先级问题
        summary = _compute_summary(uncertainties)
        can_build = summary["high"]["remaining"] == 0

        return AcceptAIAnswerResponse(
            status="success",
            uncertainty_id=request.uncertainty_id,
            message="AI 答案已采纳并保存到本体文件",
            remaining_high_priority=summary["high"]["remaining"],
            can_build_ontology=can_build
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"采纳 AI 答案失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"采纳失败: {str(e)}"
        )