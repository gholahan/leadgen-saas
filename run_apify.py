import json
import uuid
import asyncio
import os

from dotenv import load_dotenv

# Load .env before reading the key so values in the local .env file are not overwritten.
load_dotenv()

# If .env uses APIFY_KEY, map it to APIFY_API_KEY
if not os.environ.get("APIFY_API_KEY") and os.environ.get("APIFY_KEY"):
    os.environ["APIFY_API_KEY"] = os.environ["APIFY_KEY"]

from app.modules.scraping.service import ScrapingService


async def main():
    service = ScrapingService()
    job_id = uuid.uuid4()

    leads = await service.scrape_leads(
        industry="fintech",
        location="lagos, Nigeria",
        target_count=10,
        job_id=job_id,
    )

    leads_data = [lead.model_dump() for lead in leads]

    with open("leads.json", "w", encoding="utf-8") as f:
        json.dump(leads_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"Mapped {len(leads)} leads to leads.json")


if __name__ == "__main__":
    asyncio.run(main())
