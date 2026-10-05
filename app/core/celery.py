from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "leadgen",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
import socket

# TCP keepalive options using integer constants (required by redis-py).
# TCP_KEEPIDLE/INTVL/CNT are Linux-only; skip them on Windows.
_keepalive_options = {}
for _name, _val in [("TCP_KEEPIDLE", 60), ("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 5)]:
    _const = getattr(socket, _name, None)
    if _const is not None:
        _keepalive_options[_const] = _val

_redis_transport_opts = {
    "socket_keepalive": True,
    "socket_keepalive_options": _keepalive_options,
    "socket_connect_timeout": 10,
    "retry_on_timeout": True,
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    imports=(
        "app.modules.jobs.task",
        "app.modules.export.task",
        "app.modules.campaigns.tasks",
    ),
    # Apply transport options to both broker and result backend.
    broker_transport_options=_redis_transport_opts,
    redis_backend_transport_options=_redis_transport_opts,
    # Silence the deprecation warning by opting in explicitly.
    worker_cancel_long_running_tasks_on_connection_loss=True,
)

# celery_app.autodiscover_tasks(
#     [
#         "app.modules.jobs",
#         # "app.modules.scraping",
#         # "app.modules.enrichment",
#         # "app.modules.campaigns",
#     ]
# )