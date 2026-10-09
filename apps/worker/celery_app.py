from celery import Celery
from core.config.settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "ai_business_os",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Queue separation per §120 — populated with real routes as each module ships tasks.
    task_default_queue="default",
)
