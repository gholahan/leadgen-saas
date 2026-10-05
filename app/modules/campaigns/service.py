import html
import uuid
import re
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.campaigns.model import Campaign, CampaignStatus
from app.modules.campaigns.repository import (
    create_campaign,
    get_campaign,
    request_campaign_cancel,
    set_campaign_task_id,
    update_campaign_status,
)
from app.modules.jobs.repository import get_job_by_id
from app.modules.jobs.model import JobStatus

_FALLBACKS = {
    "first_name": "there",
    "company_name": "your company",
    "website": "",
    "industry": "",
    "city": "",
    "state": "",
    "country": "",
}


def render(template: str, variables: dict[str, str | None]) -> str:
    """Replace {{var}} tokens with values; use fallback if value is missing."""
    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = variables.get(key)
        raw = value if value else _FALLBACKS.get(key, "")
        return html.escape(raw) if raw else raw

    return re.sub(r"\{\{(\w+)\}\}", _replace, template)


async def create_new_campaign(
    user_id: UUID,
    job_id: UUID,
    subject: str,
    body: str,
    from_email: str | None,
    session: AsyncSession,
) -> Campaign:
    job = await get_job_by_id(job_id, session)
    if not job or job.user_id != user_id:
        raise ValueError("Job not found or does not belong to user")
    return await create_campaign(user_id, job_id, subject, body, from_email, session)


async def start_campaign(
    campaign_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> Campaign:
    from app.modules.campaigns.tasks import send_campaign_task

    campaign = await get_campaign(campaign_id, session)
    if not campaign or campaign.user_id != user_id:
        raise ValueError("Campaign not found or does not belong to user")
    if campaign.status != CampaignStatus.DRAFT:
        raise ValueError(f"Campaign is already {campaign.status.value}")
    job = await get_job_by_id(campaign.job_id, session)
    if not job or job.status != JobStatus.COMPLETED:
        raise ValueError("Campaign can only be started after its job has completed")

    # Persist the task ID and RUNNING state before the worker can pick it up.
    task_id = str(uuid.uuid4())
    claimed = await set_campaign_task_id(campaign_id, task_id, session)
    if not claimed:
        raise ValueError("Campaign is already being started")
    try:
        send_campaign_task.apply_async(args=[str(campaign_id)], task_id=task_id)
    except Exception:
        await update_campaign_status(campaign_id, CampaignStatus.FAILED, session)
        raise
    await session.refresh(campaign)
    return campaign


async def cancel_campaign(
    campaign_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> Campaign:
    from app.core.celery import celery_app

    campaign = await get_campaign(campaign_id, session)
    if not campaign or campaign.user_id != user_id:
        raise ValueError("Campaign not found or does not belong to user")
    if campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED, CampaignStatus.FAILED}:
        raise ValueError(f"Campaign is already {campaign.status.value}")

    # Graceful cancel — lets the worker finish the current recipient and check
    # is_cancelled() at the next iteration rather than hard-terminating mid-transaction.
    if campaign.celery_task_id:
        celery_app.control.revoke(campaign.celery_task_id, terminate=False)

    await request_campaign_cancel(campaign_id, session)
    await session.refresh(campaign)
    return campaign
