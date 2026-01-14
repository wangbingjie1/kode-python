"""
Celery Application Configuration

用于异步任务处理（如向量索引构建）。
如果 Celery 未安装，会优雅降级（任务会同步执行）。
"""

from kode.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from celery import Celery
    from kode.utils.config import ConfigManager

    # 获取配置
    config_manager = ConfigManager()
    celery_config = config_manager.get("celery", {})

    # 创建 Celery 应用
    celery_app = Celery(
        "kode",
        broker=celery_config.get("broker_url", "redis://localhost:6379/0"),
        backend=celery_config.get("result_backend", "redis://localhost:6379/0"),
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

    CELERY_AVAILABLE = True
    logger.info("Celery 已启用，异步任务可用")

except ImportError:
    celery_app = None
    CELERY_AVAILABLE = False
    logger.warning("Celery 未安装，异步任务将同步执行（建议安装: pip install celery redis）")
