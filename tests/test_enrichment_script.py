import asyncio
import unittest
from uuid import uuid4

from app.modules.enrichment.model import EnrichmentStatus, LeadEnrichment
from app.modules.enrichment.schema import EnrichmentResult
from test_enrichment import enrich_lead


class NotFoundProvider:
    async def enrich(self, domain, company_name=None):
        return EnrichmentResult(status="NOT_FOUND", domain=domain)


class EnrichmentScriptTests(unittest.TestCase):
    def test_no_website_outputs_lead_enrichment_record(self):
        lead_id = uuid4()
        record = asyncio.run(
            enrich_lead(
                {"id": str(lead_id), "company_name": "Example", "website": None},
                NotFoundProvider(),
                NotFoundProvider(),
            )
        )

        validated = LeadEnrichment.model_validate(record)
        self.assertEqual(validated.lead_id, lead_id)
        self.assertEqual(validated.provider, "none")
        self.assertEqual(validated.status, EnrichmentStatus.NOT_FOUND)

    def test_existing_email_is_skipped_like_production_service(self):
        result = asyncio.run(
            enrich_lead(
                {
                    "id": str(uuid4()),
                    "company_name": "Example",
                    "website": "https://example.com",
                    "email": "person@example.com",
                },
                NotFoundProvider(),
                NotFoundProvider(),
            )
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()