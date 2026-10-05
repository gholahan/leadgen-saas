import logging
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.session import engine
from app.modules.deduplication.service import deduplicate_leads
from app.modules.enrichment.service import EnrichmentService
from app.modules.jobs.model import JobStep, StepStatus
from app.modules.jobs.repository import (
    _check_is_cancelled,
    _get_step,
    _mark_job_cancelled,
    _mark_job_completed,
    _mark_job_failed,
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

    # ── 1. Scrape businesses ──────────────────────────────────────────
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

    # ── 2. Normalize data ─────────────────────────────────────────────
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

    # ── 3. Multi-Key Deduplication ────────────────────────────────────
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

    # ── 4. Persist leads (single commit) ──────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        persist_step = JobStep(job_id=job.id, step_name="persist_leads")
        session.add(persist_step)
        await session.commit()
        await session.refresh(persist_step)
        await update_job_progress(job.id, 85, session)

    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all(unique_leads)

            step = await _get_step(persist_step.id, session)
            if step:
                step.status = StepStatus.RUNNING
                session.add(step)

            await session.commit()

            step = await _get_step(persist_step.id, session)
            if step:
                step.status = StepStatus.COMPLETED
                step.output_json = {"persisted_lead_count": len(unique_leads)}
                session.add(step)

            await update_job_progress(job.id, 100, session)
            await session.commit()

    except Exception as exc:
        logger.exception("Step 'persist_leads' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            step = await _get_step(persist_step.id, session)
            if step:
                step.status = StepStatus.FAILED
                step.error_message = str(exc)
                session.add(step)
            await session.commit()
        raise

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # ── 5. Enrichment ──────────────────────────────────────────────────
    async with AsyncSession(engine, expire_on_commit=False) as session:
        enrich_step = await create_job_step(job.id, "enrich_leads", session)
        await update_step_status(enrich_step.id, StepStatus.RUNNING, session)
        await update_job_progress(job.id, 87, session)

    try:
        enrichment_service = EnrichmentService()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            enriched_leads = await enrichment_service.enrich_leads(
                unique_leads, job.id, session
            )
        emails_found = sum(1 for l in enriched_leads if l.email)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(
                enrich_step.id,
                session,
                {"total_leads": len(enriched_leads), "emails_found": emails_found},
            )
            await update_step_status(enrich_step.id, StepStatus.COMPLETED, session)
            await update_job_progress(job.id, 95, session)

    except Exception as exc:
        logger.exception("Step 'enrich_leads' failed for job %s: %s", job_id, exc)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await update_step_output(enrich_step.id, session, {}, error_message=str(exc))
            await update_step_status(enrich_step.id, StepStatus.FAILED, session)
        await _mark_job_failed(job_id, str(exc))
        return

    await _mark_job_completed(job_id)
