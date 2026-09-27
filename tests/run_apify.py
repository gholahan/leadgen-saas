import json
import uuid
import asyncio
import os

from dotenv import load_dotenv

from app.database import base as _model_registry  # noqa: F401
from app.modules.enrichment.providers.prospeo import ProspeoProvider
from app.modules.normalization.service import extract_clean_domain
from app.modules.scraping.service import ScrapingService


async def main():
    load_dotenv()
    if not os.environ.get("APIFY_API_KEY") and os.environ.get("APIFY_KEY"):
        os.environ["APIFY_API_KEY"] = os.environ["APIFY_KEY"]

    job_id = uuid.uuid4()
    scraping_service = ScrapingService()
    leads = await scraping_service.scrape_leads(
        industry="banking",
        location="lagos, Nigeria",
        target_count=10,
        job_id=job_id,
        normalize=False,
        deduplicate=False,
    )

    prospeo = ProspeoProvider()
    emails_found = 0

    for lead in leads:
        domain = extract_clean_domain(lead.website)
        if not domain or lead.email:
            continue

        try:
            result = await prospeo.enrich(domain, lead.company_name)
            if result.email:
                lead.email = result.email
                emails_found += 1
        except Exception as exc:
            print(f"Enrichment failed for {lead.company_name}: {exc}")

    leads_data = [lead.model_dump() for lead in leads]

    with open("leads.json", "w", encoding="utf-8") as f:
        json.dump(leads_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"Scraped {len(leads)} leads, enriched {emails_found} with emails")


if __name__ == "__main__":
    asyncio.run(main())
