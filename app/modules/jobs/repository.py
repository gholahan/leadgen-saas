import logging
import uuid
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.session import SessionDep, engine
from app.modules.jobs.model import Job, JobStatus, JobStep, StepStatus
from app.modules.jobs.schema import JobCreate

logger = logging.getLogger(__name__)


# ── Job CRUD ──────────────────────────────────────────────────────────

async def create_job(user_id: uuid.UUID, job_data: JobCreate, session: SessionDep):
    new_job = Job(
        id=uuid.uuid4(),
        user_id=user_id,
        industry=job_data.industry,
        location=job_data.location,
        target_count=job_data.target_count,
        status=JobStatus.PENDING,
        progress=0,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)
    return new_job


async def get_job_by_id(id: uuid.UUID, session: SessionDep):
    result = await session.exec(select(Job).where(Job.id == id))
    return result.first()


async def update_job_progress(job_id: uuid.UUID, progress: int, session: SessionDep):
    job = await get_job_by_id(job_id, session)
    if job:
        job.progress = progress
        session.add(job)
        await session.commit()
        await session.refresh(job)
    return job


async def get_user_jobs(user_id: uuid.UUID, session: SessionDep):
    result = await session.exec(select(Job).where(Job.user_id == user_id))
    return result.all()


async def update_job_status(job_id: uuid.UUID, status: JobStatus, session: SessionDep):
    job = await get_job_by_id(job_id, session)
    if job:
        job.status = status
        session.add(job)
        await session.commit()
        await session.refresh(job)
    return job


async def delete_job(job_id: uuid.UUID, session: SessionDep):
    job = await get_job_by_id(job_id, session)
    if job:
        await session.delete(job)
        await session.commit()
    return job


# ── JobStep CRUD ──────────────────────────────────────────────────────

async def create_job_step(
    job_id: uuid.UUID,
    step_name: str,
    session: SessionDep,
) -> JobStep:
    step = JobStep(
        job_id=job_id,
        step_name=step_name,
        status=StepStatus.PENDING,
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return step


async def get_job_steps(job_id: uuid.UUID, session: SessionDep):
    result = await session.exec(
        select(JobStep).where(JobStep.job_id == job_id).order_by(JobStep.started_at, JobStep.id)
    )
    return result.all()


async def update_step_status(
    step_id: uuid.UUID,
    status: StepStatus,
    session: SessionDep,
) -> JobStep | None:
    step = await _get_step(step_id, session)
    if step:
        step.status = status
        if status == StepStatus.RUNNING and step.started_at is None:
            step.started_at = datetime.now(timezone.utc)
        if status in {StepStatus.COMPLETED, StepStatus.FAILED}:
            step.completed_at = datetime.now(timezone.utc)
        session.add(step)
        await session.commit()
        await session.refresh(step)
    return step


async def update_step_output(
    step_id: uuid.UUID,
    session: SessionDep,
    output_data: dict,
    error_message: str | None = None,
) -> JobStep | None:
    step = await _get_step(step_id, session)
    if step:
        step.output_json = output_data
        if error_message is not None:
            step.error_message = error_message
        session.add(step)
        await session.commit()
        await session.refresh(step)
    return step


async def _get_step(step_id: uuid.UUID, session: SessionDep) -> JobStep | None:
    result = await session.exec(select(JobStep).where(JobStep.id == step_id))
    return result.first()


async def _check_is_cancelled(job_id: str | uuid.UUID) -> bool:
    """Return True if the job is missing or has been marked for cancellation."""
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.exec(select(Job).where(Job.id == job_id))
            job = result.first()

            if not job:
                logger.warning("Job %s not found while checking cancellation", job_id)
                return True

            return bool(job.cancel_requested or job.status == JobStatus.CANCELLED)
    except Exception:
        logger.exception("Failed to check cancellation for job %s", job_id)
        return True


async def _set_job_state(
    job_id: str | uuid.UUID,
    status: JobStatus,
    progress: int | None = None,
    error_message: str | None = None,
) -> None:
    """Atomically update the job state in the database."""
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.exec(select(Job).where(Job.id == job_id))
            job = result.first()
            if not job:
                logger.error("Job %s not found during state update", job_id)
                return

            job.status = status
            if progress is not None:
                job.progress = progress
            if error_message is not None:
                job.error_message = error_message

            if status == JobStatus.RUNNING and job.started_at is None:
                job.started_at = datetime.now(timezone.utc)
            if status in {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED}:
                if job.completed_at is None:
                    job.completed_at = datetime.now(timezone.utc)

            session.add(job)
            await session.commit()
            await session.refresh(job)
            logger.info(
                "Job %s state -> %s (progress: %d%%)",
                job_id,
                status.value,
                job.progress,
            )
    except Exception:
        logger.exception("Failed to update state for job %s", job_id)

async def _mark_job_running(job_id: str) -> None:
    """Mark the job as running in the database."""
    await _set_job_state(job_id, JobStatus.RUNNING)

async def _mark_job_completed(job_id: str) -> None:
    """Mark the job as completed in the database."""
    await _set_job_state(job_id, JobStatus.COMPLETED, progress=100)

async def _mark_job_failed(job_id: str, error_message: str) -> None:
    """Mark the job as failed in the database."""
    await _set_job_state(job_id, JobStatus.FAILED, error_message=error_message)

async def _mark_job_cancelled(job_id: str) -> None:
    """Mark the job as cancelled in the database."""
    await _set_job_state(job_id, JobStatus.CANCELLED, error_message="Job was cancelled.")