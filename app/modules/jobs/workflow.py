import logging
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.session import engine
from app.modules.deduplication.service import deduplicate_leads
from app.modules.jobs.model import StepStatus
from app.modules.jobs.repository import (
    _check_is_cancelled,
    _mark_job_cancelled,
    _mark_job_completed,
    _mark_job_running,
    create_job_step,
    get_job_by_id,
    update_job_progress,
    update_step_output,
    update_step_status,
)
from app.modules.normalization.service import normalize_leads
from app.modules.scraping.service import ScrapingService

logger = logging.getLogger(__name__)


async def _run_job_workflow(job_id: str):
    """Run the complete lead-generation workflow."""

    await _mark_job_running(job_id)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # Fetch Job Details
    async with AsyncSession(engine, expire_on_commit=False) as session:
        job = await get_job_by_id(UUID(job_id), session)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

    # ── 1. Scrape businesses ──────────────────────────────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        scrape_step = await create_job_step(job.id, "scrape_businesses", session)
        await update_step_status(scrape_step.id, StepStatus.RUNNING, session)
        await update_job_progress(job.id, 10, session)

    try:
        scraping_service = ScrapingService()
        raw_leads = await scraping_service.scrape_leads(
            industry=job.industry,
            location=job.location,
            target_count=job.target_count,
            job_id=job.id,
            normalize=False,
            deduplicate=False,
        )

        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(
                scrape_step.id,
                session,
                {"raw_leads_count": len(raw_leads)},
            )
            await update_step_status(scrape_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(job.id, 30, session)

    except Exception as exc:
        logger.exception("Step 'scrape_businesses' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(scrape_step.id, session, {}, error_message=str(exc))
            await update_step_status(scrape_step.id, StepStatus.FAILED, session)
        raise

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # ── 2. Normalize data ─────────────────────────────────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        norm_step = await create_job_step(job.id, "normalize_data", session)
        await update_step_status(norm_step.id, StepStatus.RUNNING, session)
        await update_job_progress(job.id, 40, session)

    try:
        normalized_leads = normalize_leads(raw_leads)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(
                norm_step.id,
                session,
                {"normalized_count": len(normalized_leads)},
            )
            await update_step_status(norm_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(job.id, 50, session)

    except Exception as exc:
        logger.exception("Step 'normalize_data' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(norm_step.id, session, {}, error_message=str(exc))
            await update_step_status(norm_step.id, StepStatus.FAILED, session)
        raise

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # ── 3. Multi-Key Deduplication ────────────────────────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        dedup_step = await create_job_step(job.id, "deduplicate_leads", session)
        await update_step_status(dedup_step.id, StepStatus.RUNNING, session)
        await update_job_progress(job.id, 60, session)

    try:
        initial_count = len(normalized_leads)
        unique_leads = deduplicate_leads(normalized_leads)
        duplicates_removed = initial_count - len(unique_leads)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(
                dedup_step.id,
                session,
                {
                    "input_count": initial_count,
                    "unique_count": len(unique_leads),
                    "duplicates_removed": duplicates_removed,
                },
            )
            await update_step_status(dedup_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(job.id, 75, session)

    except Exception as exc:
        logger.exception("Step 'deduplicate_leads' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(dedup_step.id, session, {}, error_message=str(exc))
            await update_step_status(dedup_step.id, StepStatus.FAILED, session)
        raise

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # ── 4. Persist leads ──────────────────────────────────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        persist_step = await create_job_step(job.id, "persist_leads", session)
        await update_step_status(persist_step.id, StepStatus.RUNNING, session)
        await update_job_progress(job.id, 85, session)

    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all(unique_leads)
            await session.commit()

            await update_step_output(
                persist_step.id,
                session,
                {"persisted_lead_count": len(unique_leads)},
            )
            await update_step_status(persist_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(job.id, 100, session)

    except Exception as exc:
        logger.exception("Step 'persist_leads' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(persist_step.id, session, {}, error_message=str(exc))
            await update_step_status(persist_step.id, StepStatus.FAILED, session)
        raise

    # ── Future steps (Enrichment, Verification, Scoring, Export) ──────────────
    # 5. Find emails: leads = await enrich_leads(leads)
    # 6. Verify emails: leads = await verify_emails(leads)
    # 7. Score/classify: leads = await score_leads(leads)
    # 8. Export: await export_leads(leads)

    await _mark_job_completed(job_id)
