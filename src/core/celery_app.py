from celery import Celery

from src.core.config import settings


celery_app = Celery(
    "semantic_retrieval",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.worker.tasks"],
)

celery_app.conf.task_default_queue = settings.celery_index_queue
