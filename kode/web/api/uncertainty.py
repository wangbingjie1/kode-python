"""
Uncertainty Management API Routes

REST endpoints for managing uncertainty Q&A workflow.
"""

from fastapi import APIRouter, HTTPException, status
from pathlib import Path
import json
from typing import Dict, Any

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
)
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)
router = APIRouter()


def _get_domains_dir(connection_name: str) -> Path:
    """获取领域文件所在目录"""
    config = ConfigManager()
    schema_path = config.get("storage.schema_path", "./schema_store")
    return Path(schema_path) / connection_name / "domains"


def _load_all_domain_files(domains_dir: Path) -> list[Dict[str, Any]]:
    """加载所有领域文件"""
    domain_data_list = []
    for domain_file in domains_dir.glob("*.json"):
        with open(domain_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["_file_path"] = str(domain_file)  # 记录文件路径
            domain_data_list.append(data)
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


def _save_domain_file(domain_file: Path, domain_data: Dict[str, Any]):
    """保存领域文件（去除临时字段）"""
    # 移除临时字段
    data_to_save = {k: v for k, v in domain_data.items() if not k.startswith("_")}
    with open(domain_file, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)


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
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            # 返回空结果而非 404，让前端显示"尚未分析"状态
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

        # 加载所有领域文件
        domain_data_list = _load_all_domain_files(domains_dir)

        # 收集所有不确定性问题
        all_uncertainties = []
        for domain_data in domain_data_list:
            domain_name = domain_data.get("domain_name", Path(domain_data["_file_path"]).stem)
            for u in domain_data.get("uncertainties", []):
                u_copy = u.copy()
                u_copy["domain"] = domain_name
                all_uncertainties.append(u_copy)

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
    答案会立即保存，无需提交整个表单。

    Args:
        request: 单个回答请求

    Returns:
        SingleAnswerResponse: 回答结果和剩余问题统计
    """
    try:
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到领域文件目录"
            )

        # 在所有领域文件中查找并更新
        found = False
        all_uncertainties = []

        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            modified = False
            for u in domain_data.get("uncertainties", []):
                all_uncertainties.append(u)

                if u.get("id") == request.uncertainty_id:
                    u["status"] = "resolved"
                    u["answer"] = request.answer
                    u["answered_at"] = datetime.now().isoformat()
                    found = True
                    modified = True

                    # 添加到业务规则
                    if "business_rules" not in domain_data:
                        domain_data["business_rules"] = []
                    domain_data["business_rules"].append({
                        "entity": u.get("entity", ""),
                        "category": u.get("category", ""),
                        "question": u.get("question", ""),
                        "answer": request.answer,
                        "added_at": datetime.now().isoformat(),
                    })

            if modified:
                _save_domain_file(domain_file, domain_data)

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到问题 ID: {request.uncertainty_id}"
            )

        # 计算剩余高优先级问题
        summary = _compute_summary(all_uncertainties)
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
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到领域文件目录"
            )

        resolved_count = 0
        not_found = []
        all_uncertainties = []

        # 遍历所有领域文件
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            modified = False
            for u in domain_data.get("uncertainties", []):
                uncertainty_id = u.get("id")
                all_uncertainties.append(u)

                if uncertainty_id in request.answers:
                    answer = request.answers[uncertainty_id]
                    u["status"] = "resolved"
                    u["answer"] = answer
                    u["answered_at"] = datetime.now().isoformat()
                    resolved_count += 1
                    modified = True

                    # 添加到业务规则
                    if "business_rules" not in domain_data:
                        domain_data["business_rules"] = []
                    domain_data["business_rules"].append({
                        "entity": u.get("entity", ""),
                        "category": u.get("category", ""),
                        "question": u.get("question", ""),
                        "answer": answer,
                        "added_at": datetime.now().isoformat(),
                    })

            if modified:
                _save_domain_file(domain_file, domain_data)

        # 检查未找到的问题
        found_ids = {u.get("id") for u in all_uncertainties if u.get("id")}
        for uid in request.answers.keys():
            if uid not in found_ids:
                not_found.append(uid)

        # 计算统计
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
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到领域文件目录"
            )

        found = False
        found_priority = None
        all_uncertainties = []

        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            modified = False
            for u in domain_data.get("uncertainties", []):
                all_uncertainties.append(u)

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
                    modified = True

            if modified:
                _save_domain_file(domain_file, domain_data)

        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到问题 ID: {request.uncertainty_id}"
            )

        # 计算统计
        summary = _compute_summary(all_uncertainties)
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