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
    """批量回答请求"""

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