from typing import Protocol

from app.modules.enrichment.schema import EnrichmentResult
from app.modules.leads.model import Lead


class EnrichmentProvider(Protocol):
    async def enrich(self, domain: str, company_name: str | None = None) -> EnrichmentResult: ...
