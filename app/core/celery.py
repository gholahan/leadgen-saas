from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "leadgen",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.config_from_object("app.core.celery_config")
celery_app.autodiscover_tasks(
    [
        "app.modules.jobs",
        "app.modules.scraping",
        "app.modules.enrichment",
        "app.modules.email",
        "app.modules.campaigns",
    ]
)