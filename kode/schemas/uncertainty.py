"""
Uncertainty Q&A Schemas

Pydantic schemas for uncertainty management API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UncertaintyItem(BaseModel):
    """单个不确定性问题"""

    id: str = Field(..., description="问题唯一 ID")
    domain: str = Field(..., description="所属业务域")
    type: str = Field(..., description="不确定性类型")
    category: str = Field(..., description="分类")
    priority: str = Field(..., description="优先级 (high/medium/low)")
    entity: str = Field(..., description="关联实体（表名）")
    question: str = Field(..., description="具体问题")
    context: Optional[str] = Field(None, description="上下文信息")
    impact: Optional[str] = Field(None, description="影响范围")
    suggestions: List[str] = Field(default_factory=list, description="建议选项")
    status: Optional[str] = Field(None, description="状态 (resolved/skipped)")
    answer: Optional[str] = Field(None, description="用户回答")
    answered_at: Optional[datetime] = Field(None, description="回答时间")


class UncertaintyGroupByDomain(BaseModel):
    """按业务域分组的不确定性列表"""

    domain: str = Field(..., description="业务域名称")
    question_count: int = Field(..., description="问题数量")
    questions: List[UncertaintyItem] = Field(..., description="问题列表")


class LoadUncertaintiesRequest(BaseModel):
    """加载不确定性请求"""

    connection_name: str = Field(..., description="数据库连接名称")
    group_by: Optional[str] = Field("domain", description="分组方式 (domain/priority)")
    limit: Optional[int] = Field(None, description="限制加载数量")


class LoadUncertaintiesResponse(BaseModel):
    """加载不确定性响应"""

    status: str = Field(..., description="状态")
    connection_name: str = Field(..., description="数据库连接名称")
    total_loaded: int = Field(..., description="加载的问题总数")
    group_by: str = Field(..., description="分组方式")
    groups: List[UncertaintyGroupByDomain] = Field(..., description="分组后的问题列表")
    message: str = Field(..., description="提示消息")


class BatchAnswerRequest(BaseModel):
    """批量回答请求（已废弃，现在通过 UserInputRequired 机制处理）"""

    connection_name: str = Field(..., description="数据库连接名称")
    answers: Dict[str, str] = Field(..., description="答案字典 {uncertainty_id: answer}")


class BatchAnswerResponse(BaseModel):
    """批量回答响应"""

    status: str = Field(..., description="状态")
    resolved_count: int = Field(..., description="已解决的问题数量")
    not_found: List[str] = Field(default_factory=list, description="未找到的问题 ID")
    remaining_high_priority: int = Field(..., description="剩余高优先级问题数")
    can_build_ontology: bool = Field(..., description="是否可以构建本体")
    message: str = Field(..., description="提示消息")


class UncertaintyStatusResponse(BaseModel):
    """不确定性状态响应"""

    status: str
    connection_name: str
    summary: Dict[str, Dict[str, int]]  # {priority: {total, resolved, skipped, remaining}}
    can_build_ontology: bool
    message: str


# ============== 新增：侧边栏问卷 API schemas ==============


class SidebarLoadRequest(BaseModel):
    """侧边栏加载不确定性问题请求"""

    connection_name: str = Field(..., description="数据库连接名称")
    priority_filter: Optional[List[str]] = Field(
        None,
        description="优先级过滤 ['high', 'medium', 'low']，默认全部"
    )
    status_filter: Optional[List[str]] = Field(
        None,
        description="状态过滤 ['pending', 'resolved', 'skipped']，默认 pending"
    )
    group_by: Optional[str] = Field("domain", description="分组方式 (domain/priority/none)")
    limit: Optional[int] = Field(None, description="限制返回数量")


class SidebarLoadResponse(BaseModel):
    """侧边栏加载不确定性问题响应"""

    status: str
    connection_name: str
    total_count: int = Field(..., description="总问题数")
    filtered_count: int = Field(..., description="过滤后的问题数")
    groups: List[UncertaintyGroupByDomain]
    summary: Dict[str, Dict[str, int]] = Field(..., description="各优先级统计")
    can_build_ontology: bool
    message: str


class SingleAnswerRequest(BaseModel):
    """单个问题回答请求"""

    connection_name: str = Field(..., description="数据库连接名称")
    uncertainty_id: str = Field(..., description="问题 ID")
    answer: str = Field(..., description="用户回答")


class SingleAnswerResponse(BaseModel):
    """单个问题回答响应"""

    status: str
    uncertainty_id: str
    message: str
    remaining_high_priority: int = Field(..., description="剩余高优先级问题数")
    can_build_ontology: bool


class SidebarBatchAnswerRequest(BaseModel):
    """侧边栏批量回答请求（独立 API，不走 SSE）"""

    connection_name: str = Field(..., description="数据库连接名称")
    answers: Dict[str, str] = Field(..., description="答案字典 {uncertainty_id: answer}")


class SidebarBatchAnswerResponse(BaseModel):
    """侧边栏批量回答响应"""

    status: str
    resolved_count: int = Field(..., description="本次解决的问题数")
    not_found: List[str] = Field(default_factory=list, description="未找到的问题 ID")
    remaining_high_priority: int = Field(..., description="剩余高优先级问题数")
    can_build_ontology: bool
    summary: Dict[str, Dict[str, int]] = Field(..., description="更新后的各优先级统计")
    message: str


class SkipQuestionRequest(BaseModel):
    """跳过问题请求"""

    connection_name: str = Field(..., description="数据库连接名称")
    uncertainty_id: str = Field(..., description="问题 ID")
    reason: Optional[str] = Field(None, description="跳过原因（可选）")


class SkipQuestionResponse(BaseModel):
    """跳过问题响应"""

    status: str
    uncertainty_id: str
    skipped_priority: str = Field(..., description="被跳过问题的优先级")
    message: str
    remaining_high_priority: int
    can_build_ontology: bool