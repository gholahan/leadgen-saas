import asyncio
import logging
from uuid import UUID

from httpx import AsyncClient, Timeout
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.enrichment.model import EnrichmentStatus
from app.modules.enrichment.providers.prospeo import ProspeoProvider
from app.modules.enrichment.repository import (
    create_lead_enrichment,
    update_lead_email,
)
from app.modules.enrichment.schema import EnrichmentResult
from app.modules.leads.model import Lead
from app.modules.normalization.service import extract_clean_domain

logger = logging.getLogger(__name__)

# Max concurrent Prospeo requests — keeps us within their rate limits
_ENRICH_CONCURRENCY = 5


class EnrichmentService:
    def __init__(self, prospeo: ProspeoProvider | None = None):
        self.prospeo = prospeo or ProspeoProvider()

    async def enrich_leads(
        self,
        leads: list[Lead],
        job_id: UUID,
        session: AsyncSession,
    ) -> list[Lead]:
        """Enrich leads using Prospeo, reusing a single HTTP connection pool
        and processing up to _ENRICH_CONCURRENCY leads at a time."""

        # One shared client for all leads — avoids a TLS handshake per lead
        async with AsyncClient(timeout=Timeout(20.0)) as client:
            sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

            async def _enrich_one(lead: Lead) -> Lead:
                if lead.email:
                    logger.debug("Lead %s already has email, skipping", lead.id)
                    return lead

                domain = extract_clean_domain(lead.website)
                if not domain:
                    logger.debug("Lead %s has no domain, skipping", lead.id)
                    await create_lead_enrichment(
                        lead_id=str(lead.id),
                        provider="none",
                        email=None,
                        email_type=None,
                        email_score=None,
                        domain=None,
                        status=EnrichmentStatus.NOT_FOUND,
                        session=session,
                    )
                    return lead

                logger.debug("Enriching lead %s via Prospeo", lead.id)
                async with sem:
                    result: EnrichmentResult = await self.prospeo.enrich(
                        domain, company_name=lead.company_name, client=client
                    )

                await create_lead_enrichment(
                    lead_id=str(lead.id),
                    provider="prospeo",
                    email=result.email,
                    email_type=result.email_type,
                    email_score=result.email_score,
                    domain=result.domain,
                    status=EnrichmentStatus(result.status),
                    session=session,
                )

                if result.email:
                    await update_lead_email(str(lead.id), result.email, session)
                    lead.email = result.email
                    logger.info("Enriched email for lead %s", lead.id)

                return lead

            enriched = await asyncio.gather(*(_enrich_one(lead) for lead in leads))

        return list(enriched)
