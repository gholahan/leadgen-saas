from celery import Celery
from celery.utils.log import get_task_logger

from app.core.celery import celery_app
from app.database import base as _model_registry
import asyncio
from app.modules.jobs.workflow import _run_job_workflow
from app.modules.jobs.repository import _mark_job_failed


logger = get_task_logger(__name__)


async def _run_job_task(job_id: str) -> None:
    try:
        await _run_job_workflow(job_id)
    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        await _mark_job_failed(job_id, str(exc))



@celery_app.task(
    name="jobs.process",
    soft_time_limit=1000,
)
def process_job_task(job_id: str):
    asyncio.run(_run_job_task(job_id))