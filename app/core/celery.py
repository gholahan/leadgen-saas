from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "leadgen",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Socket-level keepalive options prevent Aiven/managed Redis from dropping
# idle connections with "Connection closed by server".
_redis_transport_opts = {
    "socket_keepalive": True,
    "socket_keepalive_options": {
        # Start sending keepalives after 60 s of idle; then every 10 s;
        # declare dead after 5 missed probes.
        "TCP_KEEPIDLE": 60,
        "TCP_KEEPINTVL": 10,
        "TCP_KEEPCNT": 5,
    },
    # Raise immediately instead of blocking forever on a broken socket.
    "socket_connect_timeout": 10,
    "retry_on_timeout": True,
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    imports=(
        "app.modules.jobs.task",
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