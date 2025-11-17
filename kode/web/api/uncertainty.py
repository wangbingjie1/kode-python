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
)
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


def _get_uncertainty_file(connection_name: str) -> Path:
    """获取 uncertainty 数据文件路径"""
    config = ConfigManager()
    schema_path = config.get("storage.schema_path", "./schema_store")
    return Path(schema_path) / connection_name / "uncertainties.json"


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
        uncertainty_file = _get_uncertainty_file(request.connection_name)

        if not uncertainty_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uncertainties file not found. Run DomainUncertaintyAnalyzer first."
            )

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 收集所有未解决的高优先级问题
        high_uncertainties = [
            u for u in data.get("uncertainties_by_priority", {}).get("high", [])
            if u.get("status") not in ["resolved", "skipped"]
        ]

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
            connection_name=data.get("connection_name", request.connection_name),
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
    批量回答不确定性问题

    Args:
        request: 批量回答请求（包含连接名和答案字典）

    Returns:
        BatchAnswerResponse: 批量回答结果
    """
    try:
        uncertainty_file = _get_uncertainty_file(request.connection_name)

        if not uncertainty_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uncertainties file not found"
            )

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        from datetime import datetime

        resolved_count = 0
        not_found = []

        # 批量更新
        for uncertainty_id, answer in request.answers.items():
            found = False
            for priority in ["high", "medium", "low"]:
                uncertainties = data.get("uncertainties_by_priority", {}).get(priority, [])
                for u in uncertainties:
                    # 生成 ID（如果没有）
                    if "id" not in u:
                        u["id"] = f"{u.get('domain')}_{u.get('entity')}_{uncertainties.index(u)}"

                    if u["id"] == uncertainty_id:
                        u["status"] = "resolved"
                        u["answer"] = answer
                        u["answered_at"] = datetime.now().isoformat()
                        resolved_count += 1
                        found = True
                        break
                if found:
                    break

            if not found:
                not_found.append(uncertainty_id)

        # 保存更新后的数据
        with open(uncertainty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 统计剩余未解决的高优先级问题
        remaining_high = [
            u for u in data.get("uncertainties_by_priority", {}).get("high", [])
            if u.get("status") not in ["resolved", "skipped"]
        ]

        return BatchAnswerResponse(
            status="success",
            resolved_count=resolved_count,
            not_found=not_found,
            remaining_high_priority=len(remaining_high),
            can_build_ontology=len(remaining_high) == 0,
            message=(
                f"已批量记录 {resolved_count} 个回答。剩余 {len(remaining_high)} 个高优先级问题。"
                if len(remaining_high) > 0
                else f"已批量记录 {resolved_count} 个回答。所有高优先级问题已解决！可以开始构建本体。"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch answer uncertainties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch answer uncertainties: {str(e)}"
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
        uncertainty_file = _get_uncertainty_file(connection_name)

        if not uncertainty_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uncertainties file not found. Run DomainUncertaintyAnalyzer first."
            )

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 统计各优先级的解决情况
        summary = {}
        for priority in ["high", "medium", "low"]:
            uncertainties = data.get("uncertainties_by_priority", {}).get(priority, [])
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
            connection_name=data.get("connection_name", connection_name),
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