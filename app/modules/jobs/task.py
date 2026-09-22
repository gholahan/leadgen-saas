from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery import celery_app
from app.database.session import get_session
from app.modules.jobs.model import Job, JobStatus
import asyncio
from app.modules.jobs.workflow import _run_job_workflow
from app.modules.jobs.repository import _mark_job_failed


logger = get_task_logger(__name__)



@celery_app.task(
    name="jobs.process",
    soft_time_limit=1000,
)
def process_job_task(self, job_id: str):
    try:
        asyncio.run(_run_job_workflow(job_id))
    except Exception as e:
        logger.exception("Job %s failed: %s", job_id, e)
        asyncio.run(_mark_job_failed(job_id, str(e)))