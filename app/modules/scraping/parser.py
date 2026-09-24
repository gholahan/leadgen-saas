import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.modules.deduplication.service import deduplicate_leads
from app.modules.leads.model import Lead
from app.modules.normalization.service import normalize_leads
from app.modules.scraping.utils import extract_place_id

logger = logging.getLogger(__name__)


def parse_leads(
    apify_results: list[dict[str, Any]],
    job_id: UUID,
    normalize: bool = True,
    deduplicate: bool = True,
) -> list[Lead]:
    """Parse raw Apify result items into Lead models, with optional normalization and deduplication."""
    leads: list[Lead] = []

    for item in apify_results:
        categories = item.get("categories") or []
        industry = categories[0] if categories else item.get("search_term")

        rating = item.get("rating")
        rating_decimal = Decimal(str(rating)) if rating is not None else None

        google_maps_url = item.get("google_maps_url")
        place_id = extract_place_id(google_maps_url)

        lead = Lead(
            job_id=job_id,
            company_name=item.get("name") or "Unknown Business",
            website=item.get("website"),
            phone=item.get("phone"),
            address=item.get("address"),
            city=item.get("city"),
            state=item.get("state"),
            country=item.get("country_code"),
            industry=industry,
            google_maps_url=google_maps_url,
            place_id=place_id,
            rating=rating_decimal,
            review_count=item.get("review_count"),
        )
        leads.append(lead)

    if normalize:
        leads = normalize_leads(leads)

    if deduplicate:
        leads = deduplicate_leads(leads)

    return leads

