from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlmodel import select as sa_select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.enrichment.model import LeadEnrichment, EnrichmentStatus
from app.modules.leads.model import Lead


async def create_lead_enrichment(
    lead_id: str,
    provider: str,
    email: str | None,
    email_type: str | None,
    email_score: int | None,
    domain: str | None,
    status: EnrichmentStatus,
    session: AsyncSession,
) -> LeadEnrichment:
    record = LeadEnrichment(
        lead_id=lead_id,
        provider=provider,
        email=email,
        email_type=email_type,
        email_score=email_score,
        domain=domain,
        status=status,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_lead_enrichments(lead_id: str, session: AsyncSession) -> list[LeadEnrichment]:
    result = await session.exec(
        sa_select(LeadEnrichment).where(LeadEnrichment.lead_id == lead_id)
    )
    return result.all()


async def update_lead_email(lead_id: str, email: str, session: AsyncSession) -> Lead | None:
    result = await session.exec(sa_select(Lead).where(Lead.id == lead_id))
    lead = result.first()
    if lead and email:
        lead.email = email
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
    return lead
