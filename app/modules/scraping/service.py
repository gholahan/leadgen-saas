from uuid import UUID

from app.modules.leads.model import Lead
from app.modules.scraping.parser import parse_leads
from app.modules.scraping.providers.apify import ApifyProvider


class ScrapingService:
    def __init__(self, provider: ApifyProvider | None = None):
        self.provider = provider or ApifyProvider()

    async def scrape_leads(
        self,
        industry: str,
        location: str,
        target_count: int,
        job_id: UUID,
        normalize: bool = False,
        deduplicate: bool = False,
    ) -> list[Lead]:
        raw_results = await self.provider.scrape_businesses(
            industry=industry,
            location=location,
            target_count=target_count,
        )
        leads = parse_leads(
            raw_results,
            job_id=job_id,
            normalize=normalize,
            deduplicate=deduplicate,
        )
        return leads
