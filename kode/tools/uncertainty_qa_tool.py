"""Uncertainty Q&A management tool for interactive ontology building."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from kode.tools.base import KodeTool
from kode.utils.config import ConfigManager
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)


class UncertaintyQAManagerInput(BaseModel):
    """Input schema for UncertaintyQAManager."""

    connection_name: str = Field(description="Database connection name")
    action: str = Field(
        description="Action to perform: 'load', 'batch_load', 'answer', 'batch_answer', 'skip', 'status'"
    )
    uncertainty_id: Optional[str] = Field(
        default=None,
        description="Uncertainty ID to answer/skip (required for 'answer'/'skip' action)"
    )
    answer: Optional[str] = Field(
        default=None,
        description="User's answer to the uncertainty (required for 'answer' action)"
    )
    batch_answers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Dict of {uncertainty_id: answer} for batch_answer action"
    )
    group_by: Optional[str] = Field(
        default="domain",
        description="Group questions by: 'domain' (default) or 'priority'"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Limit number of questions to load (for batch_load)"
    )


class UncertaintyQAManager(KodeTool):
    """
    管理不确定性问答过程，记录用户回答并追踪进度。

    这个工具用于：
    1. 加载并展示待解决的不确定性问题
    2. 记录用户对每个问题的回答
    3. 追踪问答进度，判断是否可以继续构建本体

    工作流程：
    - action='load' → 返回所有待解决的高优先级问题
    - action='answer' → 记录用户对某个问题的回答
    - action='status' → 检查当前进度，判断是否所有 high 问题已解决
    """

    name: str = "UncertaintyQAManager"
    description: str = """Manage uncertainty Q&A process for ontology building.

    Actions:
    - 'load': Load all unresolved high-priority uncertainties
    - 'batch_load': Load questions grouped by domain/priority (supports limit)
    - 'answer': Record user's answer to a specific uncertainty
    - 'batch_answer': Record multiple answers at once (batch_answers={id: answer, ...})
    - 'skip': Mark a medium/low priority question as skipped
    - 'status': Check progress (how many high-priority questions remain)

    Use this tool to:
    1. Present high-priority questions to user before ontology building
    2. Record user answers and track progress (single or batch mode)
    3. Allow skipping non-critical questions
    4. Verify all critical questions are answered before proceeding
    """

    args_schema: Type[BaseModel] = UncertaintyQAManagerInput
    requires_permission: bool = False

    def _run(
        self,
        connection_name: str,
        action: str,
        uncertainty_id: Optional[str] = None,
        answer: Optional[str] = None,
        batch_answers: Optional[Dict[str, str]] = None,
        group_by: str = "domain",
        limit: Optional[int] = None
    ) -> str:
        """
        Execute Q&A management action.

        Args:
            connection_name: Database connection name
            action: Action to perform
            uncertainty_id: ID of uncertainty to answer/skip
            answer: User's answer
            batch_answers: Dict of {uncertainty_id: answer} for batch operations
            group_by: Group questions by 'domain' or 'priority'
            limit: Limit number of questions to load

        Returns:
            Result as JSON
        """
        try:
            # 🔥 获取领域目录（而不是单一的 uncertainties.json 文件）
            domains_dir = self._get_domains_dir(connection_name)

            if action == "load":
                return self._load_uncertainties(domains_dir)
            elif action == "batch_load":
                return self._batch_load_uncertainties(domains_dir, group_by, limit)
            elif action == "answer":
                if not uncertainty_id or not answer:
                    return json.dumps({
                        "status": "error",
                        "message": "uncertainty_id and answer are required for 'answer' action"
                    }, indent=2, ensure_ascii=False)
                return self._record_answer(domains_dir, uncertainty_id, answer)
            elif action == "batch_answer":
                if not batch_answers:
                    return json.dumps({
                        "status": "error",
                        "message": "batch_answers dict is required for 'batch_answer' action"
                    }, indent=2, ensure_ascii=False)
                return self._batch_record_answers(domains_dir, batch_answers)
            elif action == "skip":
                if not uncertainty_id:
                    return json.dumps({
                        "status": "error",
                        "message": "uncertainty_id is required for 'skip' action"
                    }, indent=2, ensure_ascii=False)
                return self._skip_uncertainty(domains_dir, uncertainty_id)
            elif action == "status":
                return self._check_status(domains_dir)
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}. Valid actions: load, batch_load, answer, batch_answer, skip, status"
                }, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"UncertaintyQAManager failed: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to manage uncertainties: {str(e)}"
            }, indent=2, ensure_ascii=False)

    def _get_domains_dir(self, connection_name: str) -> Path:
        """获取领域文件所在目录"""
        config = ConfigManager()
        schema_path = config.get("storage.schema_path", "./schema_store")
        return Path(schema_path) / connection_name / "domains"

    def _load_all_domain_files(self, domains_dir: Path) -> List[Dict[str, Any]]:
        """加载所有领域文件的数据"""
        domain_data_list = []
        for domain_file in domains_dir.glob("*.json"):
            with open(domain_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file_path"] = domain_file  # 记录文件路径
                domain_data_list.append(data)
        return domain_data_list

    def _save_domain_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """保存领域文件"""
        # 移除临时字段
        data_to_save = {k: v for k, v in data.items() if k != "_file_path"}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

    def _load_uncertainties(self, domains_dir: Path) -> str:
        """从各个领域文件加载所有待解决的不确定性"""
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": f"Domains directory not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

        # 遍历所有领域文件，收集未解决的高优先级问题
        high_uncertainties = []
        domain_files = list(domains_dir.glob("*.json"))

        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            domain_name = domain_data.get("domain_name", domain_file.stem)
            uncertainties = domain_data.get("uncertainties", [])

            # 筛选未解决的高优先级问题
            for u in uncertainties:
                if u.get("priority", "medium").lower() == "high" and u.get("status") != "resolved":
                    # 添加领域信息
                    u["domain"] = domain_name
                    # 生成唯一 ID（如果没有）
                    if "id" not in u:
                        u["id"] = f"{domain_name}_{u.get('entity', 'unknown')}_{len(high_uncertainties)}"
                    high_uncertainties.append(u)

        return json.dumps({
            "status": "success",
            "total_high_priority": len(high_uncertainties),
            "unresolved_count": len(high_uncertainties),
            "questions": high_uncertainties,
            "message": (
                f"找到 {len(high_uncertainties)} 个高优先级未解决问题。"
                "必须全部回答后才能构建本体。"
            )
        }, indent=2, ensure_ascii=False)

    def _record_answer(
        self,
        domains_dir: Path,
        uncertainty_id: str,
        answer: str
    ) -> str:
        """
        记录用户对某个不确定性的回答。

        🔥 新逻辑：
        1. 在对应的领域文件中标记 uncertainty 为 resolved
        2. 将答案添加到领域文件的 business_rules 字段
        """
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": "Domains directory not found"
            }, indent=2, ensure_ascii=False)

        # 遍历所有领域文件，查找对应的 uncertainty
        domain_files = list(domains_dir.glob("*.json"))
        found = False
        updated_domain = None

        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            uncertainties = domain_data.get("uncertainties", [])

            for u in uncertainties:
                # 生成 ID（如果没有）
                if "id" not in u:
                    u["id"] = f"{domain_data.get('domain_name', domain_file.stem)}_{u.get('entity', 'unknown')}_{uncertainties.index(u)}"

                if u["id"] == uncertainty_id:
                    # 标记为已解决
                    u["status"] = "resolved"
                    u["answer"] = answer
                    u["answered_at"] = datetime.now().isoformat()

                    # 🔥 核心变化：将答案添加到 business_rules
                    if "business_rules" not in domain_data:
                        domain_data["business_rules"] = []

                    business_rule = {
                        "entity": u.get("entity", ""),
                        "category": u.get("category", ""),
                        "question": u.get("question", ""),
                        "answer": answer,
                        "added_at": datetime.now().isoformat()
                    }
                    domain_data["business_rules"].append(business_rule)

                    # 保存更新后的领域文件
                    with open(domain_file, "w", encoding="utf-8") as f:
                        json.dump(domain_data, f, indent=2, ensure_ascii=False)

                    found = True
                    updated_domain = domain_data.get("domain_name", domain_file.stem)
                    break

            if found:
                break

        if not found:
            return json.dumps({
                "status": "error",
                "message": f"Uncertainty with ID '{uncertainty_id}' not found in any domain"
            }, indent=2, ensure_ascii=False)

        # 统计所有领域中剩余的高优先级问题
        remaining_high = 0
        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            for u in domain_data.get("uncertainties", []):
                if u.get("priority", "medium").lower() == "high" and u.get("status") != "resolved":
                    remaining_high += 1

        return json.dumps({
            "status": "success",
            "resolved_id": uncertainty_id,
            "updated_domain": updated_domain,
            "answer": answer,
            "remaining_high_priority": remaining_high,
            "can_build_ontology": remaining_high == 0,
            "message": (
                f"已记录回答到领域 {updated_domain}。剩余 {remaining_high} 个高优先级问题。"
                if remaining_high > 0
                else f"已记录回答到领域 {updated_domain}。所有高优先级问题已解决！可以开始构建本体。"
            )
        }, indent=2, ensure_ascii=False)

    # 🔥 已删除：_preprocess_domain_rules 和 _compress_domain_uncertainties
    # 原因：规则现在直接存储在各领域 JSON 文件的 business_rules 字段，不再生成独立的 *_rules.txt 文件

    # TODO: 以下方法仍需重构以适配新的领域文件结构：
    # - _batch_load_uncertainties
    # - _batch_record_answers
    # - _check_status
    # - _skip_uncertainty

    def _check_status(self, domains_dir: Path) -> str:
        """检查当前进度（新架构：从领域文件读取）"""
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": "Domains directory not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

        # 统计各优先级的解决情况
        summary = {"high": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0},
                   "medium": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0},
                   "low": {"total": 0, "resolved": 0, "skipped": 0, "remaining": 0}}

        domain_files = list(domains_dir.glob("*.json"))

        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            uncertainties = domain_data.get("uncertainties", [])
            for u in uncertainties:
                priority = u.get("priority", "low")
                status = u.get("status", "pending")

                summary[priority]["total"] += 1
                if status == "resolved":
                    summary[priority]["resolved"] += 1
                elif status == "skipped":
                    summary[priority]["skipped"] += 1
                else:
                    summary[priority]["remaining"] += 1

        can_build = summary["high"]["remaining"] == 0

        return json.dumps({
            "status": "success",
            "summary": summary,
            "can_build_ontology": can_build,
            "message": (
                "所有高优先级问题已解决，可以构建本体！"
                if can_build
                else f"还有 {summary['high']['remaining']} 个高优先级问题待解决，必须先回答这些问题。"
            )
        }, indent=2, ensure_ascii=False)

    def _batch_load_uncertainties(
        self,
        domains_dir: Path,
        group_by: str = "domain",
        limit: Optional[int] = None
    ) -> str:
        """批量加载不确定性问题，支持分组和限制数量（新架构：从领域文件读取）"""
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": "Domains directory not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

        # 收集所有未解决的高优先级问题
        high_uncertainties = []
        domain_files = list(domains_dir.glob("*.json"))

        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            domain_name = domain_data.get("domain_name", domain_file.stem)
            uncertainties = domain_data.get("uncertainties", [])

            for u in uncertainties:
                if u.get("priority", "medium").lower() == "high" and u.get("status") not in ["resolved", "skipped"]:
                    # 添加领域信息
                    u["domain"] = domain_name
                    # 生成唯一 ID（如果没有）
                    if "id" not in u:
                        u["id"] = f"{domain_name}_{u.get('entity', 'unknown')}_{len(high_uncertainties)}"
                    high_uncertainties.append(u)

        # 应用 limit
        if limit and limit > 0:
            high_uncertainties = high_uncertainties[:limit]

        # 分组
        if group_by == "domain":
            groups = {}
            for u in high_uncertainties:
                domain = u.get("domain", "unknown")
                if domain not in groups:
                    groups[domain] = []
                groups[domain].append(u)

            grouped_result = [
                {
                    "domain": domain,
                    "question_count": len(questions),
                    "questions": questions
                }
                for domain, questions in groups.items()
            ]
        elif group_by == "priority":
            grouped_result = [{
                "priority": "high",
                "question_count": len(high_uncertainties),
                "questions": high_uncertainties
            }]
        else:
            grouped_result = high_uncertainties

        return json.dumps({
            "status": "success",
            "total_loaded": len(high_uncertainties),
            "group_by": group_by,
            "groups": grouped_result,
            "message": f"已加载 {len(high_uncertainties)} 个高优先级问题，按 {group_by} 分组展示。前端会渲染批量问答表单，请等待用户填写并提交。"
        }, indent=2, ensure_ascii=False)

    def _batch_record_answers(
        self,
        domains_dir: Path,
        batch_answers: Dict[str, str]
    ) -> str:
        """批量记录多个问题的回答（新架构：更新领域文件）"""
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": "Domains directory not found"
            }, indent=2, ensure_ascii=False)

        resolved_count = 0
        not_found = []
        domain_files = list(domains_dir.glob("*.json"))

        # 批量更新
        for uncertainty_id, answer in batch_answers.items():
            found = False

            for domain_file in domain_files:
                with open(domain_file, "r", encoding="utf-8") as f:
                    domain_data = json.load(f)

                uncertainties = domain_data.get("uncertainties", [])

                for u in uncertainties:
                    # 生成 ID（如果没有）
                    if "id" not in u:
                        u["id"] = f"{domain_data.get('domain_name', domain_file.stem)}_{u.get('entity', 'unknown')}_{uncertainties.index(u)}"

                    if u["id"] == uncertainty_id:
                        u["status"] = "resolved"
                        u["answer"] = answer
                        u["answered_at"] = datetime.now().isoformat()

                        # 添加到 business_rules
                        if "business_rules" not in domain_data:
                            domain_data["business_rules"] = []

                        business_rule = {
                            "entity": u.get("entity", ""),
                            "category": u.get("category", ""),
                            "question": u.get("question", ""),
                            "answer": answer,
                            "added_at": datetime.now().isoformat()
                        }
                        domain_data["business_rules"].append(business_rule)

                        # 保存更新
                        with open(domain_file, "w", encoding="utf-8") as f:
                            json.dump(domain_data, f, indent=2, ensure_ascii=False)

                        resolved_count += 1
                        found = True
                        break

                if found:
                    break

            if not found:
                not_found.append(uncertainty_id)

        # 统计剩余高优先级问题
        remaining_high = 0
        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            for u in domain_data.get("uncertainties", []):
                if u.get("priority", "medium").lower() == "high" and u.get("status") not in ["resolved", "skipped"]:
                    remaining_high += 1

        return json.dumps({
            "status": "success",
            "resolved_count": resolved_count,
            "not_found": not_found,
            "remaining_high_priority": remaining_high,
            "can_build_ontology": remaining_high == 0,
            "message": (
                f"已批量记录 {resolved_count} 个回答。剩余 {remaining_high} 个高优先级问题。"
                if remaining_high > 0
                else f"已批量记录 {resolved_count} 个回答。所有高优先级问题已解决！可以开始构建本体。"
            )
        }, indent=2, ensure_ascii=False)

    def _skip_uncertainty(self, domains_dir: Path, uncertainty_id: str) -> str:
        """标记某个问题为跳过（仅允许 medium/low 优先级，新架构：更新领域文件）"""
        if not domains_dir.exists():
            return json.dumps({
                "status": "error",
                "message": "Domains directory not found"
            }, indent=2, ensure_ascii=False)

        found = False
        found_priority = None
        domain_files = list(domains_dir.glob("*.json"))

        for domain_file in domain_files:
            with open(domain_file, "r", encoding="utf-8") as f:
                domain_data = json.load(f)

            uncertainties = domain_data.get("uncertainties", [])

            for u in uncertainties:
                if "id" not in u:
                    u["id"] = f"{domain_data.get('domain_name', domain_file.stem)}_{u.get('entity', 'unknown')}_{uncertainties.index(u)}"

                if u["id"] == uncertainty_id:
                    found_priority = u.get("priority", "medium")
                    if found_priority == "high":
                        return json.dumps({
                            "status": "error",
                            "message": "不能跳过高优先级问题！必须回答所有 high 优先级问题才能构建本体。"
                        }, indent=2, ensure_ascii=False)

                    u["status"] = "skipped"
                    u["skipped_at"] = datetime.now().isoformat()

                    # 保存更新
                    with open(domain_file, "w", encoding="utf-8") as f:
                        json.dump(domain_data, f, indent=2, ensure_ascii=False)

                    found = True
                    break

            if found:
                break

        if not found:
            return json.dumps({
                "status": "error",
                "message": f"Uncertainty with ID '{uncertainty_id}' not found"
            }, indent=2, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "skipped_id": uncertainty_id,
            "priority": found_priority,
            "message": f"已跳过 {found_priority} 优先级问题。"
        }, indent=2, ensure_ascii=False)
