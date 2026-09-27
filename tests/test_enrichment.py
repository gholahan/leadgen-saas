"""Run the email providers against the leads in leads.json."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.modules.enrichment.providers.prospeo import ProspeoProvider
from app.modules.normalization.service import extract_clean_domain


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "leads.json"
OUTPUT_PATH = ROOT / "leads_enrichment_test.json"


async def enrich_lead(
    lead: dict[str, Any],
    hunter: Any,
    prospeo: Any,
) -> dict[str, Any] | None:
    if lead.get("email"):
        return None

    domain = extract_clean_domain(lead.get("website"))
    result: dict[str, Any] | None = None
    provider_used = "none"

    if domain:
        for provider_name, provider, company_name in (
            ("hunter", hunter, None),
            ("prospeo", prospeo, lead.get("company_name")),
        ):
            provider_used = provider_name
            try:
                provider_result = await provider.enrich(domain, company_name)
                result = provider_result.model_dump(mode="json")
            except Exception as exc:
                result = {
                    "status": "FAILED",
                    "domain": domain,
                }

            if result.get("email"):
                break

    if result is None:
        result = {"status": "NOT_FOUND", "domain": domain}

    return {
        "id": str(uuid4()),
        "lead_id": lead["id"],
        "provider": provider_used,
        "email": result.get("email"),
        "email_type": result.get("email_type"),
        "email_score": result.get("email_score"),
        "domain": result.get("domain", domain),
        "status": result.get("status", "NOT_FOUND"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> None:
    leads = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(leads, list):
        raise ValueError("leads.json must contain a JSON array of leads")

    hunter = ProspeoProvider()
    prospeo = ProspeoProvider()
    enrichment_records = []

    for lead in leads:
        record = await enrich_lead(lead, hunter, prospeo)
        if record is not None:
            enrichment_records.append(record)

    OUTPUT_PATH.write_text(
        json.dumps(enrichment_records, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    emails_found = sum(bool(record["email"]) for record in enrichment_records)
    print(
        f"Created {len(enrichment_records)} enrichment records; "
        f"emails found: {emails_found}"
    )
    print(f"Wrote results to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
