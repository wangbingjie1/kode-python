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
    批量回答不确定性问题

    ⭐ 核心功能：保存答案后，自动触发 Agent 继续执行（检查状态 → 构建本体）

    Args:
        request: 批量回答请求（包含连接名、答案字典、对话ID、用户ID）

    Returns:
        BatchAnswerResponse: 批量回答结果
    """
    try:
        domains_dir = _get_domains_dir(request.connection_name)

        if not domains_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domains directory not found"
            )

        from datetime import datetime

        resolved_count = 0
        not_found = []

        # 🔥 批量更新：遍历所有领域文件
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            modified = False
            uncertainties = domain_data.get("uncertainties", [])

            for u in uncertainties:
                # 生成 ID（如果没有）
                if "id" not in u:
                    u["id"] = f"{domain_data.get('domain_name', domain_file.stem)}_{u.get('entity', 'unknown')}_{uncertainties.index(u)}"

                # 检查是否需要更新
                if u["id"] in request.answers:
                    answer = request.answers[u["id"]]
                    u["status"] = "resolved"
                    u["answer"] = answer
                    u["answered_at"] = datetime.now().isoformat()

                    # 🔥 添加到 business_rules
                    if "business_rules" not in domain_data:
                        domain_data["business_rules"] = []

                    domain_data["business_rules"].append({
                        "entity": u.get("entity", ""),
                        "category": u.get("category", ""),
                        "question": u.get("question", ""),
                        "answer": answer,
                        "added_at": datetime.now().isoformat()
                    })

                    resolved_count += 1
                    modified = True

            # 保存修改后的领域文件
            if modified:
                with open(domain_file, "w", encoding="utf-8") as f:
                    json.dump(domain_data, f, indent=2, ensure_ascii=False)

        # 检查未找到的 ID
        resolved_ids = set()
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)
            for u in domain_data.get("uncertainties", []):
                if "id" in u:
                    resolved_ids.add(u["id"])

        not_found = [uid for uid in request.answers.keys() if uid not in resolved_ids]

        # 统计剩余未解决的高优先级问题
        remaining_high = 0
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)
            for u in domain_data.get("uncertainties", []):
                if u.get("priority", "medium").lower() == "high" and u.get("status") not in ["resolved", "skipped"]:
                    remaining_high += 1

        response = BatchAnswerResponse(
            status="success",
            resolved_count=resolved_count,
            not_found=not_found,
            remaining_high_priority=remaining_high,
            can_build_ontology=remaining_high == 0,
            message=(
                f"已批量记录 {resolved_count} 个回答。剩余 {remaining_high} 个高优先级问题。"
                if remaining_high > 0
                else f"已批量记录 {resolved_count} 个回答。所有高优先级问题已解决！可以开始构建本体。"
            )
        )

        # 🔥 自动触发 Agent 继续执行：保存一条系统消息到数据库
        try:
            from kode.database.session import SessionLocal
            from kode.models.message import Message
            from datetime import datetime

            db = SessionLocal()
            try:
                # 创建系统消息（告知 Agent 用户已提交答案）
                system_message = Message(
                    conversation_id=request.conversation_id,
                    role="user",
                    content=f"[系统] 用户已提交批量问卷答案（共 {resolved_count} 个）。请调用 UncertaintyQAManager(action='status') 检查进度，然后继续执行。",
                    metadata={
                        "auto_generated": True,
                        "trigger": "batch_answer_completion",
                        "resolved_count": resolved_count,
                        "remaining_high": remaining_high,
                        "can_build_ontology": remaining_high == 0,
                        "connection_name": request.connection_name
                    },
                    created_at=datetime.utcnow()
                )
                db.add(system_message)
                db.commit()
                logger.info(f"[Auto-Resume] System message saved for conversation {request.conversation_id}")
            except Exception as db_error:
                logger.error(f"[Auto-Resume] Failed to save system message: {db_error}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"[Auto-Resume] Error during auto-resume: {e}")
            # 不影响主流程，继续返回

        return response

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