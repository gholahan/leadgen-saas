import asyncio
import logging
import re as _re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import UUID

import httpx
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.celery import celery_app
from app.core.config import settings
from app.database.session import make_celery_engine
from app.modules.campaigns.model import CampaignStatus
from app.modules.campaigns.repository import (
    create_recipients,
    get_campaign,
    is_cancelled,
    mark_recipient_failed,
    mark_recipient_sending,
    mark_recipient_sent,
    update_campaign_status,
)
from app.modules.campaigns.service import render
from app.modules.enrichment.model import EnrichmentStatus, LeadEnrichment
from app.modules.leads.model import Lead
from app.modules.jobs.model import Job, JobStatus

logger = logging.getLogger(__name__)


def _retry_after_seconds(value: str | None, attempt: int) -> float:
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at is None:
                    return float(2 ** attempt)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)


async def _send_via_brevo(
    *,
    from_email: str,
    to: str,
    subject: str,
    html: str,
    client: httpx.AsyncClient,
) -> str:
    """Send one email via Brevo. Returns the Brevo message ID."""
    if not settings.BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not configured")
    # Strip HTML tags for the plain-text fallback so clients that don't render HTML
    # still show readable content rather than raw markup.
    text_content = _re.sub(r"<[^>]+>", "", html).strip()
    for attempt in range(4):
        resp = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "sender": {"email": from_email},
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": html,
                "textContent": text_content,
            },
            timeout=15,
        )
        if resp.status_code == 429 and attempt < 3:
            delay = _retry_after_seconds(resp.headers.get("Retry-After"), attempt)
            logger.warning(
                "Brevo rate-limited email; retrying attempt %d/4 in %.1f seconds",
                attempt + 2,
                delay,
            )
            await asyncio.sleep(delay)
            continue
        if resp.is_error:
            raise RuntimeError(
                f"Brevo API returned {resp.status_code}: {resp.text}"
            )
        logger.info("Brevo accepted email (HTTP %d)", resp.status_code)
        return resp.json().get("messageId", "")
    raise RuntimeError("Brevo rate-limit retry attempts exhausted")


# Snapshot of lead data needed for personalization — avoids detached instance errors
# when the lead is accessed outside its original session.
class _LeadSnapshot:
    __slots__ = ("company_name", "website", "industry", "city", "state", "country")

    def __init__(self, lead: Lead):
        self.company_name = lead.company_name
        self.website = lead.website
        self.industry = lead.industry
        self.city = lead.city
        self.state = lead.state
        self.country = lead.country


async def _run_campaign(campaign_id: str) -> None:
    campaign_uuid = UUID(campaign_id)
    engine = make_celery_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        campaign = await get_campaign(campaign_uuid, session)
        if not campaign:
            logger.error("Campaign %s not found", campaign_id)
            return
        if campaign.status != CampaignStatus.RUNNING:
            raise RuntimeError(f"Campaign {campaign_id} is not RUNNING")

        job_result = await session.exec(select(Job).where(Job.id == campaign.job_id))
        job = job_result.first()
        if not job or job.status != JobStatus.COMPLETED:
            raise RuntimeError("Campaign source job is missing or has not completed")

        # Resolve sender: campaign.from_email → user.email
        from app.modules.auth.model import User
        user_result = await session.exec(select(User).where(User.id == campaign.user_id))
        user = user_result.first()
        from_email = campaign.from_email or (user.email if user else None)
        if not from_email or not from_email.strip():
            raise RuntimeError("Campaign has no sender address")
        from_email = from_email.strip()

        # Snapshot campaign template fields before session closes
        subject_template = campaign.subject
        body_template = campaign.body
        campaign_uuid = campaign.id
        job_id = campaign.job_id

        # Resolve enriched leads for this job
        enrichments_result = await session.exec(
            select(LeadEnrichment, Lead)
            .join(Lead, Lead.id == LeadEnrichment.lead_id)
            .where(
                Lead.job_id == job_id,
                LeadEnrichment.status == EnrichmentStatus.FOUND,
                LeadEnrichment.email.isnot(None),
                func.trim(LeadEnrichment.email) != "",
            )
        )
        rows = enrichments_result.all()

        lead_snapshots = {}
        recipient_data = []
        for enrichment, lead in rows:
            email = enrichment.email.strip() if enrichment.email else ""
            if not email:
                continue
            recipient_data.append((lead.id, enrichment.id, email, enrichment.first_name))
            lead_snapshots[enrichment.id] = _LeadSnapshot(lead)

        recipient_records = await create_recipients(campaign_uuid, recipient_data, session)
        recipients = [
            (recipient, lead_snapshots[recipient.enrichment_id])
            for recipient in recipient_records
            if recipient.enrichment_id in lead_snapshots
        ]

        logger.info(
            "Campaign %s: %d enriched recipient(s) eligible for Brevo",
            campaign_id,
            len(recipients),
        )
        if not recipients:
            await update_campaign_status(campaign_uuid, CampaignStatus.COMPLETED, session)
            logger.info(
                "Campaign %s: skipping Brevo; no recipients have a FOUND enrichment "
                "with a non-empty email",
                campaign_id,
            )
            return

    # Send emails — each recipient in its own session to isolate failures
    sent_count = 0
    failed_count = 0

    async with httpx.AsyncClient() as http_client:
        for recipient, lead_snap in recipients:
            # Cooperative cancellation check between recipients
            async with AsyncSession(engine, expire_on_commit=False) as session:
                if await is_cancelled(UUID(campaign_id), session):
                    await update_campaign_status(UUID(campaign_id), CampaignStatus.CANCELLED, session)
                    logger.info("Campaign %s cancelled after %d sent", campaign_id, sent_count)
                    return

            variables = {
                "first_name": recipient.first_name,
                "company_name": lead_snap.company_name,
                "website": lead_snap.website,
                "industry": lead_snap.industry,
                "city": lead_snap.city,
                "state": lead_snap.state,
                "country": lead_snap.country,
            }
            subject = render(subject_template, variables)
            body = render(body_template, variables)

            async with AsyncSession(engine, expire_on_commit=False) as session:
                claimed = await mark_recipient_sending(recipient.id, session)
            if not claimed:
                continue

            try:
                logger.info(
                    "Campaign %s: sending recipient %s via Brevo",
                    campaign_id,
                    recipient.email,
                )
                message_id = await _send_via_brevo(
                    from_email=from_email,
                    to=recipient.email,
                    subject=subject,
                    html=body,
                    client=http_client,
                )
            except Exception as exc:
                failed_count += 1
                async with AsyncSession(engine, expire_on_commit=False) as session:
                    await mark_recipient_failed(recipient.id, str(exc), session)
                logger.warning(
                    "Campaign %s: Brevo delivery failed for %s — %s",
                    campaign_id,
                    recipient.email,
                    exc,
                )
                continue

            async with AsyncSession(engine, expire_on_commit=False) as session:
                await mark_recipient_sent(recipient.id, message_id, session)
            sent_count += 1
            logger.info("Campaign %s: sent to %s", campaign_id, recipient.email)
            await asyncio.sleep(0.35)  # ~3 req/s — stay within Brevo rate limits

    # Mark FAILED if every recipient failed, COMPLETED otherwise (partial failures visible on recipients)
    final_status = (
        CampaignStatus.FAILED
        if failed_count > 0 and sent_count == 0
        else CampaignStatus.COMPLETED
    )
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await update_campaign_status(UUID(campaign_id), final_status, session)

    logger.info(
        "Campaign %s %s — sent: %d, failed: %d",
        campaign_id, final_status.value, sent_count, failed_count,
    )


async def _record_task_failure(campaign_id: str, *, terminated: bool = False) -> None:
    try:
        campaign_uuid = UUID(campaign_id)
        engine = make_celery_engine()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            campaign = await get_campaign(campaign_uuid, session)
            if not campaign or campaign.status in {
                CampaignStatus.COMPLETED,
                CampaignStatus.FAILED,
                CampaignStatus.CANCELLED,
            }:
                return
            status = (
                CampaignStatus.CANCELLED
                if terminated or campaign.cancel_requested
                else CampaignStatus.FAILED
            )
            await update_campaign_status(campaign_uuid, status, session)
    except Exception:
        logger.exception("Could not record failure for campaign %s", campaign_id)


@celery_app.task(name="campaigns.send")
def send_campaign_task(campaign_id: str) -> None:
    try:
        asyncio.run(_run_campaign(campaign_id))
    except SystemExit as exc:
        asyncio.run(_record_task_failure(campaign_id, terminated=True))
        logger.info("Campaign %s terminated: %s", campaign_id, exc)
        raise
    except Exception:
        asyncio.run(_record_task_failure(campaign_id))
        logger.exception("Campaign %s crashed", campaign_id)
        raise
