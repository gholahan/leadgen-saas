from app.modules.jobs.repository import (
    _mark_job_running,
    _mark_job_completed,
    _mark_job_cancelled,
    _check_is_cancelled,
)


async def _run_job_workflow(job_id: str):
    """Run the complete lead-generation workflow."""

    await _mark_job_running(job_id)
    
    # Add workflow steps here

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 1. Scrape businesses
    # leads = await scrape_businesses(...)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 2. Normalize data
    # leads = normalize_leads(leads)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 3. Remove duplicates
    # leads = deduplicate_leads(leads)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 4. Find emails
    # leads = await enrich_leads(leads)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 5. Verify emails
    # leads = await verify_emails(leads)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 6. Score/classify
    # leads = await score_leads(leads)

    if await _check_is_cancelled(job_id):
        await _mark_job_cancelled(job_id)
        return

    # 7. Export
    # await export_leads(leads)

    await _mark_job_completed(job_id)