import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.enrichment.service import EnrichmentService


class EnrichmentServiceTests(unittest.TestCase):
    def test_lead_without_website_creates_not_found_record(self):
        lead = SimpleNamespace(
            id=uuid4(),
            email=None,
            website=None,
            company_name="No Website Inc",
        )
        session = AsyncMock()

        async def run_test():
            with patch(
                "app.modules.enrichment.service.create_lead_enrichment",
                new_callable=AsyncMock,
            ) as create_enrichment:
                service = EnrichmentService()
                result = await service.enrich_leads([lead], uuid4(), session)
                return result, create_enrichment

        result, create_enrichment = asyncio.run(run_test())

        self.assertEqual(result, [lead])
        create_enrichment.assert_awaited_once()
        self.assertEqual(
            create_enrichment.await_args.kwargs["status"].value,
            "NOT_FOUND",
        )
        self.assertNotIn("raw_response", create_enrichment.await_args.kwargs)

    def test_concurrent_leads_persist_database_writes_sequentially(self):
        leads = [
            SimpleNamespace(
                id=uuid4(),
                email=None,
                website=None,
                company_name=f"Company {index}",
            )
            for index in range(2)
        ]
        session = AsyncMock()
        active_writes = 0
        max_active_writes = 0

        async def create_enrichment(**kwargs):
            nonlocal active_writes, max_active_writes
            active_writes += 1
            max_active_writes = max(max_active_writes, active_writes)
            await asyncio.sleep(0)
            active_writes -= 1

        async def run_test():
            with patch(
                "app.modules.enrichment.service.create_lead_enrichment",
                new_callable=AsyncMock,
                side_effect=create_enrichment,
            ) as create_mock:
                service = EnrichmentService()
                result = await service.enrich_leads(leads, uuid4(), session)
                return result, create_mock

        result, create_mock = asyncio.run(run_test())

        self.assertEqual(result, leads)
        self.assertEqual(create_mock.await_count, 2)
        self.assertEqual(max_active_writes, 1)


if __name__ == "__main__":
    unittest.main()
