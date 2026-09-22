import uuid
from celery.result import AsyncResult

from app.database.session import SessionDep
from app.modules.jobs.model import Job, JobStatus, JobStep, StepStatus
from app.modules.jobs.repository import create_job
from app.modules.jobs.repository import delete_job as repo_delete_job
from app.modules.jobs.repository import get_job_by_id as repo_get_job_by_id
from app.modules.jobs.repository import get_user_jobs as repo_get_user_jobs
from app.modules.jobs.repository import get_job_steps
from app.modules.jobs.repository import update_job_status
from app.modules.jobs.schema import JobCreate
from app.modules.jobs.task import process_job_task


# ── Exceptions ────────────────────────────────────────────────────────────

class JobNotFound(Exception):
    pass


class JobAlreadyFinished(Exception):
    pass


# ── Business Logic ────────────────────────────────────────────────────────

async def create_new_job(user_id: uuid.UUID, job_data: JobCreate, session: SessionDep):
    job = await create_job(user_id, job_data, session)
    task = process_job_task.delay(str(job.id))

    job.celery_task_id = task.id # Store the Celery task ID in the job record
    job.status = JobStatus.PENDING
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_user_jobs(session: SessionDep, user):
    return await repo_get_user_jobs(user.id, session)


async def get_job_by_id(job_id: uuid.UUID, session: SessionDep):
    return await repo_get_job_by_id(job_id, session)


async def get_user_job(job_id: uuid.UUID, user_id: uuid.UUID, session: SessionDep):
    job = await repo_get_job_by_id(job_id, session)
    if not job or job.user_id != user_id:
        raise JobNotFound()
    return job


async def get_job_steps(job_id: uuid.UUID, session: SessionDep):
    job = await repo_get_job_by_id(job_id, session)
    if not job:
        raise JobNotFound()
    return await get_job_steps(job_id, session)


async def cancel_job_service(
    job_id: uuid.UUID,
    user_id: uuid.UUID,
    session: SessionDep,
):
    """Cancel a job using cooperative cancellation.

    Sets cancel_requested=True on the job, which the Celery task checks at
    each workflow step. No forceful worker termination is used.
    """
    job = await get_user_job(job_id, user_id, session)

    if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        raise JobAlreadyFinished()

    job.cancel_requested = True
    job.status = JobStatus.CANCELLED
    job.completed_at = None
    job.error_message = "Cancellation requested — waiting for worker to acknowledge"

    await session.commit()
    await session.refresh(job)

    return job


async def delete_job(job_id: uuid.UUID, session: SessionDep):
    return await repo_delete_job(job_id, session)

