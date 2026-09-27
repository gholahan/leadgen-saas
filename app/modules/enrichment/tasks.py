import uuid

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.celery import celery_app
from app.database.session import engine
from app.modules.enrichment.service import EnrichmentService
from app.modules.jobs.model import StepStatus
from app.modules.jobs.repository import (
    _check_is_cancelled,
    create_job_step,
    update_job_progress,
    update_step_output,
    update_step_status,
)
from app.modules.leads.model import Lead

try:
    from celery.utils.log import get_task_logger
    logger = get_task_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def _run_enrichment_task(job_id: str) -> None:
    if await _check_is_cancelled(job_id):
        return

    async with AsyncSession(engine, expire_on_commit=False) as session:
        enrich_step = await create_job_step(uuid.UUID(job_id), "enrich_leads", session)
        await update_step_status(enrich_step.id, StepStatus.RUNNING, session)
        await update_job_progress(uuid.UUID(job_id), 85, session)

    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.exec(
                select(Lead).where(Lead.job_id == uuid.UUID(job_id))
            )
            leads = result.all()

            service = EnrichmentService()
            enriched_leads = await service.enrich_leads(
                leads, uuid.UUID(job_id), session
            )
            emails_found = sum(1 for l in enriched_leads if l.email)

            await update_step_output(
                enrich_step.id,
                session,
                {"total_leads": len(leads), "emails_found": emails_found},
            )
            await update_step_status(enrich_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(uuid.UUID(job_id), 95, session)

    except Exception as exc:
        logger.exception("Step 'enrich_leads' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(
                enrich_step.id, session, {}, error_message=str(exc)
            )
            await update_step_status(enrich_step.id, StepStatus.FAILED, session)
        raise


@celery_app.task(
    name="enrichment.process",
    soft_time_limit=1000,
)
def enrich_job_task(job_id: str):
    import asyncio
    asyncio.run(_run_enrichment_task(job_id))
