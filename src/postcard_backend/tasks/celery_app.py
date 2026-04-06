from celery import Celery

from postcard_backend.core.config import get_settings

settings = get_settings()

celery_app = Celery("postcard_backend", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
