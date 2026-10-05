from datetime import datetime, timezone
from uuid import UUID

import logging

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.campaigns.model import Campaign, CampaignRecipient, CampaignStatus, RecipientStatus

logger = logging.getLogger(__name__)


async def create_campaign(
    user_id: UUID,
    job_id: UUID,
    subject: str,
    body: str,
    from_email: str | None,
    session: AsyncSession,
) -> Campaign:
    campaign = Campaign(
        user_id=user_id,
        job_id=job_id,
        subject=subject,
        body=body,
        from_email=from_email,
        status=CampaignStatus.DRAFT,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def get_campaign(campaign_id: UUID, session: AsyncSession) -> Campaign | None:
    result = await session.exec(select(Campaign).where(Campaign.id == campaign_id))
    return result.first()


async def get_user_campaigns(user_id: UUID, session: AsyncSession) -> list[Campaign]:
    result = await session.exec(select(Campaign).where(Campaign.user_id == user_id))
    return list(result.all())


async def update_campaign_status(
    campaign_id: UUID, status: CampaignStatus, session: AsyncSession
) -> None:
    result = await session.exec(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.one()
    campaign.status = status
    if status in {CampaignStatus.COMPLETED, CampaignStatus.FAILED, CampaignStatus.CANCELLED}:
        campaign.completed_at = datetime.now(timezone.utc)
    session.add(campaign)
    await session.commit()


async def set_campaign_task_id(
    campaign_id: UUID, task_id: str, session: AsyncSession
) -> bool:
    result = await session.exec(
        update(Campaign)
        .where(Campaign.id == campaign_id, Campaign.status == CampaignStatus.DRAFT)
        .values(celery_task_id=task_id, status=CampaignStatus.RUNNING)
    )
    await session.commit()
    return result.rowcount == 1


async def request_campaign_cancel(campaign_id: UUID, session: AsyncSession) -> None:
    result = await session.exec(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.one()
    campaign.cancel_requested = True
    session.add(campaign)
    await session.commit()


async def is_cancelled(campaign_id: UUID, session: AsyncSession) -> bool:
    result = await session.exec(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.first()
    return campaign is None or campaign.cancel_requested


async def create_recipients(
    campaign_id: UUID,
    recipients: list[tuple[UUID, UUID, str, str | None]],
    session: AsyncSession,
) -> list[CampaignRecipient]:
    unique_recipients = {}
    ordered_enrichment_ids = []
    for lead_id, enrichment_id, email, first_name in recipients:
        ordered_enrichment_ids.append(enrichment_id)
        unique_recipients.setdefault(
            enrichment_id,
            {
                "campaign_id": campaign_id,
                "lead_id": lead_id,
                "enrichment_id": enrichment_id,
                "email": email,
                "first_name": first_name,
                "status": RecipientStatus.PENDING,
            },
        )

    if unique_recipients:
        statement = (
            insert(CampaignRecipient)
            .values(list(unique_recipients.values()))
            .on_conflict_do_nothing(
                index_elements=[CampaignRecipient.campaign_id, CampaignRecipient.enrichment_id]
            )
        )
        await session.exec(statement)
        await session.commit()
        result = await session.exec(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.enrichment_id.in_(list(unique_recipients)),
            )
        )
        existing = {recipient.enrichment_id: recipient for recipient in result.all()}
        dropped = set(unique_recipients) - set(existing)
        if dropped:
            logger.warning(
                "create_recipients: %d enrichment(s) dropped due to unique constraint conflict for campaign %s",
                len(dropped), campaign_id,
            )
        return [existing[enrichment_id] for enrichment_id in ordered_enrichment_ids]
    return []


async def mark_recipient_sending(recipient_id: UUID, session: AsyncSession) -> bool:
    result = await session.exec(
        update(CampaignRecipient)
        .where(
            CampaignRecipient.id == recipient_id,
            CampaignRecipient.status.in_([RecipientStatus.PENDING, RecipientStatus.FAILED]),
        )
        .values(status=RecipientStatus.SENDING, error_message=None)
    )
    await session.commit()
    return result.rowcount == 1


async def mark_recipient_sent(
    recipient_id: UUID, provider_message_id: str, session: AsyncSession
) -> None:
    result = await session.exec(select(CampaignRecipient).where(CampaignRecipient.id == recipient_id))
    r = result.one()
    r.status = RecipientStatus.SENT
    r.provider_message_id = provider_message_id
    r.sent_at = datetime.now(timezone.utc)
    session.add(r)
    await session.commit()


async def mark_recipient_failed(
    recipient_id: UUID, error: str, session: AsyncSession
) -> None:
    result = await session.exec(select(CampaignRecipient).where(CampaignRecipient.id == recipient_id))
    r = result.one()
    r.status = RecipientStatus.FAILED
    r.error_message = error
    session.add(r)
    await session.commit()


async def get_recipients(campaign_id: UUID, session: AsyncSession) -> list[CampaignRecipient]:
    result = await session.exec(
        select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
    )
    return list(result.all())
