"""
Plan Model

订阅套餐模型，定义不同的付费计划。
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON
from datetime import datetime
import uuid

from kode.database.session import Base


class Plan(Base):
    """订阅套餐模型"""

    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False, index=True)  # 套餐名称
    display_name = Column(String(100), nullable=False)  # 显示名称（中文）
    description = Column(Text, nullable=True)  # 套餐描述

    # 定价
    price = Column(Float, nullable=False)  # 价格（元/月）
    billing_period = Column(String(20), default="monthly")  # monthly, yearly

    # 配额限制
    token_quota = Column(Integer, nullable=False)  # 每月 Token 额度
    message_quota = Column(Integer, nullable=False)  # 每月消息条数限制
    conversation_quota = Column(Integer, nullable=False)  # 同时保持的对话数限制
    database_connection_quota = Column(Integer, default=0)  # 数据库连接数限制

    # 功能开关
    database_access = Column(Boolean, default=False)  # 是否支持数据库连接
    advanced_analysis = Column(Boolean, default=False)  # 是否支持高级分析
    ontology_building = Column(Boolean, default=False)  # 是否支持本体构建
    priority_support = Column(Boolean, default=False)  # 是否享受优先支持

    # 其他配置
    features = Column(JSON, nullable=True)  # 额外功能配置（JSON）
    is_active = Column(Boolean, default=True)  # 是否启用
    sort_order = Column(Integer, default=0)  # 排序顺序

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, price={self.price})>"
