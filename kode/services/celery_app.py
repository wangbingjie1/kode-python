"""
Celery Application Configuration

用于异步任务处理（如向量索引构建）。
"""

from celery import Celery
from kode.utils.config import get_config

# 获取配置
config = get_config()

# 创建 Celery 应用
celery_app = Celery(
    "kode",
    broker=config.get("celery", {}).get("broker_url", "redis://localhost:6379/0"),
    backend=config.get("celery", {}).get("result_backend", "redis://localhost:6379/0"),
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,  # 每次只拉取一个任务
)

# 自动发现任务
celery_app.autodiscover_tasks(["kode.services"])
