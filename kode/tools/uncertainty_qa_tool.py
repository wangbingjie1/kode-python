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
            # 获取 uncertainty 数据文件路径
            uncertainty_file = self._get_uncertainty_file(connection_name)

            if action == "load":
                return self._load_uncertainties(uncertainty_file)
            elif action == "batch_load":
                return self._batch_load_uncertainties(uncertainty_file, group_by, limit)
            elif action == "answer":
                if not uncertainty_id or not answer:
                    return json.dumps({
                        "status": "error",
                        "message": "uncertainty_id and answer are required for 'answer' action"
                    }, indent=2, ensure_ascii=False)
                return self._record_answer(uncertainty_file, uncertainty_id, answer)
            elif action == "batch_answer":
                if not batch_answers:
                    return json.dumps({
                        "status": "error",
                        "message": "batch_answers dict is required for 'batch_answer' action"
                    }, indent=2, ensure_ascii=False)
                return self._batch_record_answers(uncertainty_file, batch_answers)
            elif action == "skip":
                if not uncertainty_id:
                    return json.dumps({
                        "status": "error",
                        "message": "uncertainty_id is required for 'skip' action"
                    }, indent=2, ensure_ascii=False)
                return self._skip_uncertainty(uncertainty_file, uncertainty_id)
            elif action == "status":
                return self._check_status(uncertainty_file)
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

    def _get_uncertainty_file(self, connection_name: str) -> Path:
        """获取 uncertainty 数据文件路径"""
        config = ConfigManager()
        schema_path = config.get("storage.schema_path", "./schema_store")
        return Path(schema_path) / connection_name / "uncertainties.json"

    def _load_uncertainties(self, uncertainty_file: Path) -> str:
        """加载所有待解决的不确定性"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": f"Uncertainties file not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 筛选未解决的高优先级问题
        high_uncertainties = [
            u for u in data.get("uncertainties_by_priority", {}).get("high", [])
            if u.get("status") != "resolved"
        ]

        # 为每个问题生成唯一 ID（如果没有的话）
        for idx, u in enumerate(high_uncertainties):
            if "id" not in u:
                u["id"] = f"{u.get('domain')}_{u.get('entity')}_{idx}"

        return json.dumps({
            "status": "success",
            "connection_name": data.get("connection_name"),
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
        uncertainty_file: Path,
        uncertainty_id: str,
        answer: str
    ) -> str:
        """记录用户对某个不确定性的回答"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": "Uncertainties file not found"
            }, indent=2, ensure_ascii=False)

        # 加载数据
        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 查找并更新对应的 uncertainty
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
                    found = True
                    break
            if found:
                break

        if not found:
            return json.dumps({
                "status": "error",
                "message": f"Uncertainty with ID '{uncertainty_id}' not found"
            }, indent=2, ensure_ascii=False)

        # 保存更新后的数据
        with open(uncertainty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 统计剩余未解决的高优先级问题
        remaining_high = [
            u for u in data.get("uncertainties_by_priority", {}).get("high", [])
            if u.get("status") != "resolved"
        ]

        return json.dumps({
            "status": "success",
            "resolved_id": uncertainty_id,
            "answer": answer,
            "remaining_high_priority": len(remaining_high),
            "can_build_ontology": len(remaining_high) == 0,
            "message": (
                f"已记录回答。剩余 {len(remaining_high)} 个高优先级问题。"
                if len(remaining_high) > 0
                else "所有高优先级问题已解决！可以开始构建本体。"
            )
        }, indent=2, ensure_ascii=False)

    def _preprocess_domain_rules(
        self,
        schema_dir: Path,
        connection_name: str,
        uncertainty_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        预处理领域规则：为每个域生成精简的规则文件。

        Args:
            schema_dir: Schema 存储目录
            connection_name: 数据库连接名
            uncertainty_data: 不确定性数据

        Returns:
            预处理结果统计
        """
        try:
            domains_dir = schema_dir / "domains"
            if not domains_dir.exists():
                return {"status": "error", "message": "domains/ directory not found"}

            # 按域分组High问题
            high_uncertainties = uncertainty_data.get("uncertainties_by_priority", {}).get("high", [])
            domain_groups = {}
            for u in high_uncertainties:
                if u.get("status") != "resolved":
                    continue
                domain = u.get("domain", "unknown")
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(u)

            # 为每个域生成规则文件
            processed = 0
            for domain_name, uncertainties in domain_groups.items():
                rules_text = self._compress_domain_uncertainties(uncertainties)
                if rules_text:
                    rules_file = domains_dir / f"{domain_name}_rules.txt"
                    with open(rules_file, "w", encoding="utf-8") as f:
                        f.write(rules_text)
                    processed += 1
                    logger.info(f"✅ 生成 {rules_file.name} ({len(uncertainties)} 条规则)")

            return {
                "status": "success",
                "domains_processed": processed,
                "total_rules": len(high_uncertainties)
            }

        except Exception as e:
            logger.error(f"预处理领域规则失败: {e}")
            return {"status": "error", "message": str(e)}

    def _compress_domain_uncertainties(self, uncertainties: List[Dict[str, Any]]) -> str:
        """
        格式化领域不确定性为结构化文本（保留完整问题和答案）。

        不再做过度压缩，因为已经按领域分割了，每个领域的规则数量不多。
        """
        if not uncertainties:
            return ""

        lines = []
        lines.append("# 用户已确认的业务规则（构建本体时必须遵守）")
        lines.append("")

        for idx, unc in enumerate(uncertainties, 1):
            entity = unc.get("entity", "")
            question = unc.get("question", "").strip()
            answer = unc.get("answer", "").strip()
            category = unc.get("category", "")
            unc_type = unc.get("type", "")

            if not answer:
                continue

            # 每条规则保留：实体名、问题类型、问题、用户答案
            lines.append(f"## 规则 {idx}: {entity}")
            if category:
                lines.append(f"**类型**: {category}")
            lines.append(f"**问题**: {question}")
            lines.append(f"**用户确认**: {answer}")
            lines.append("")

        if len(lines) <= 2:  # 只有标题，没有实际规则
            return ""

        return "\n".join(lines)

    def _check_status(self, uncertainty_file: Path) -> str:
        """检查当前进度"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": "Uncertainties file not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

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

        return json.dumps({
            "status": "success",
            "connection_name": data.get("connection_name"),
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
        uncertainty_file: Path,
        group_by: str = "domain",
        limit: Optional[int] = None
    ) -> str:
        """批量加载不确定性问题，支持分组和限制数量"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": "Uncertainties file not found. Run DomainUncertaintyAnalyzer first."
            }, indent=2, ensure_ascii=False)

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
            # 虽然当前只加载 high，但保留扩展性
            grouped_result = [{
                "priority": "high",
                "question_count": len(high_uncertainties),
                "questions": high_uncertainties
            }]
        else:
            # 不分组，直接返回列表
            grouped_result = high_uncertainties

        return json.dumps({
            "status": "success",
            "connection_name": data.get("connection_name"),
            "total_loaded": len(high_uncertainties),
            "group_by": group_by,
            "groups": grouped_result,
            "message": f"已加载 {len(high_uncertainties)} 个高优先级问题，按 {group_by} 分组展示。",
            "requires_user_input": True,  # 标记需要用户输入，Agent应该暂停并等待
            "next_tool": "UncertaintyQAManager",  # 提示下一步应该调用的工具
            "next_action": "batch_answer"  # 提示下一步的action
        }, indent=2, ensure_ascii=False)

    def _batch_record_answers(
        self,
        uncertainty_file: Path,
        batch_answers: Dict[str, str]
    ) -> str:
        """批量记录多个问题的回答"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": "Uncertainties file not found"
            }, indent=2, ensure_ascii=False)

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        resolved_count = 0
        not_found = []

        # 批量更新
        for uncertainty_id, answer in batch_answers.items():
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

        # 🔥 新增：如果所有High问题已解决，自动预处理领域规则
        connection_name = data.get("connection_name")
        all_high_resolved = all(
            u.get("status") in ["resolved", "skipped"]
            for u in data.get("uncertainties_by_priority", {}).get("high", [])
        )

        if all_high_resolved and connection_name:
            preprocessing_result = self._preprocess_domain_rules(uncertainty_file.parent, connection_name, data)
            logger.info(f"✅ 预处理完成：{preprocessing_result.get('domains_processed', 0)} 个领域")

        # 统计剩余未解决的高优先级问题
        remaining_high = [
            u for u in data.get("uncertainties_by_priority", {}).get("high", [])
            if u.get("status") not in ["resolved", "skipped"]
        ]

        return json.dumps({
            "status": "success",
            "resolved_count": resolved_count,
            "not_found": not_found,
            "remaining_high_priority": len(remaining_high),
            "can_build_ontology": len(remaining_high) == 0,
            "message": (
                f"已批量记录 {resolved_count} 个回答。剩余 {len(remaining_high)} 个高优先级问题。"
                if len(remaining_high) > 0
                else f"已批量记录 {resolved_count} 个回答。所有高优先级问题已解决！可以开始构建本体。"
            )
        }, indent=2, ensure_ascii=False)

    def _skip_uncertainty(self, uncertainty_file: Path, uncertainty_id: str) -> str:
        """标记某个问题为跳过（仅允许 medium/low 优先级）"""
        if not uncertainty_file.exists():
            return json.dumps({
                "status": "error",
                "message": "Uncertainties file not found"
            }, indent=2, ensure_ascii=False)

        with open(uncertainty_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        found = False
        found_priority = None

        for priority in ["high", "medium", "low"]:
            uncertainties = data.get("uncertainties_by_priority", {}).get(priority, [])
            for u in uncertainties:
                if "id" not in u:
                    u["id"] = f"{u.get('domain')}_{u.get('entity')}_{uncertainties.index(u)}"

                if u["id"] == uncertainty_id:
                    found_priority = priority
                    if priority == "high":
                        return json.dumps({
                            "status": "error",
                            "message": "不能跳过高优先级问题！必须回答所有 high 优先级问题才能构建本体。"
                        }, indent=2, ensure_ascii=False)

                    u["status"] = "skipped"
                    u["skipped_at"] = datetime.now().isoformat()
                    found = True
                    break
            if found:
                break

        if not found:
            return json.dumps({
                "status": "error",
                "message": f"Uncertainty with ID '{uncertainty_id}' not found"
            }, indent=2, ensure_ascii=False)

        # 保存更新后的数据
        with open(uncertainty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "skipped_id": uncertainty_id,
            "priority": found_priority,
            "message": f"已跳过 {found_priority} 优先级问题。"
        }, indent=2, ensure_ascii=False)
