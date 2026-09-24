import logging
import re
from typing import Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.leads.model import Lead
from app.modules.normalization.service import extract_clean_domain, is_generic_domain

logger = logging.getLogger(__name__)


def _clean_str_for_key(value: str | None) -> str:
    """Normalize string for key generation (lowercased alphanumeric)."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _generate_dedup_keys(lead: Lead) -> list[str]:
    """Generate prioritized deduplication keys for a lead.

    Priority order:
    1. place_id: Google Place ID (most reliable)
    2. domain: Clean website root domain (excluding social/generic platforms)
    3. phone: Normalized E.164 phone number
    4. name_location: Normalized name + city + country
    """
    keys: list[str] = []

    # 1. Place ID
    if lead.place_id:
        keys.append(f"place_id:{lead.place_id}")

    # 2. Website root domain
    domain = extract_clean_domain(lead.website)
    if domain and not is_generic_domain(domain):
        keys.append(f"domain:{domain}")

    # 3. Phone number
    if lead.phone and len(lead.phone) >= 7:
        keys.append(f"phone:{lead.phone}")

    # 4. Company Name + City + Country
    clean_name = _clean_str_for_key(lead.company_name)
    clean_city = _clean_str_for_key(lead.city)
    clean_country = _clean_str_for_key(lead.country)

    if clean_name and (clean_city or clean_country):
        keys.append(f"name_loc:{clean_name}:{clean_city}:{clean_country}")

    return keys


def _merge_lead_data(target: Lead, source: Lead) -> None:
    """Merge non-empty fields from source into target to enrich the survivor record."""
    if not target.website and source.website:
        target.website = source.website
    if not target.email and source.email:
        target.email = source.email
    if not target.phone and source.phone:
        target.phone = source.phone
    if not target.address and source.address:
        target.address = source.address
    if not target.city and source.city:
        target.city = source.city
    if not target.state and source.state:
        target.state = source.state
    if not target.country and source.country:
        target.country = source.country
    if not target.industry and source.industry:
        target.industry = source.industry
    if not target.place_id and source.place_id:
        target.place_id = source.place_id
    if not target.google_maps_url and source.google_maps_url:
        target.google_maps_url = source.google_maps_url

    # Preserve richer review/rating stats
    source_reviews = source.review_count or 0
    target_reviews = target.review_count or 0
    if source_reviews > target_reviews:
        target.review_count = source.review_count
        target.rating = source.rating or target.rating


def deduplicate_leads(leads: list[Lead]) -> list[Lead]:
    """In-memory multi-key deduplication for a batch of leads.

    Identifies duplicates using Place ID, domain, phone, and name+location.
    Merges richer data from duplicate records into the survivor.
    """
    key_to_lead_index: dict[str, int] = {}
    unique_leads: list[Lead] = []

    for lead in leads:
        lead_keys = _generate_dedup_keys(lead)
        existing_index: int | None = None

        # Check if any key matches an already processed lead
        for key in lead_keys:
            if key in key_to_lead_index:
                existing_index = key_to_lead_index[key]
                break

        if existing_index is not None:
            # Duplicate found: merge source lead data into target lead
            target_lead = unique_leads[existing_index]
            _merge_lead_data(target_lead, lead)

            # Re-index target with any newly discovered keys from source
            for key in lead_keys:
                key_to_lead_index[key] = existing_index

            logger.debug(
                "Merged duplicate lead '%s' into '%s'",
                lead.company_name,
                target_lead.company_name,
            )
        else:
            # New unique lead
            new_index = len(unique_leads)
            unique_leads.append(lead)
            for key in lead_keys:
                key_to_lead_index[key] = new_index

    duplicates_count = len(leads) - len(unique_leads)
    if duplicates_count > 0:
        logger.info(
            "Deduplication completed: %d duplicates merged/removed from %d total leads (resulting in %d unique leads).",
            duplicates_count,
            len(leads),
            len(unique_leads),
        )

    return unique_leads


async def deduplicate_against_db(session: AsyncSession, leads: list[Lead]) -> tuple[list[Lead], list[Lead]]:
    """Check leads against existing database records.

    Returns:
        (new_leads, existing_duplicate_leads)
    """
    place_ids = [lead.place_id for lead in leads if lead.place_id]
    phones = [lead.phone for lead in leads if lead.phone]

    existing_place_ids: set[str] = set()
    existing_phones: set[str] = set()

    if place_ids:
        statement = select(Lead.place_id).where(Lead.place_id.in_(place_ids))
        result = await session.exec(statement)
        existing_place_ids = set(result.all())

    if phones:
        statement = select(Lead.phone).where(Lead.phone.in_(phones))
        result = await session.exec(statement)
        existing_phones = set(result.all())

    new_leads: list[Lead] = []
    duplicate_leads: list[Lead] = []

    for lead in leads:
        if (lead.place_id and lead.place_id in existing_place_ids) or (lead.phone and lead.phone in existing_phones):
            duplicate_leads.append(lead)
        else:
            new_leads.append(lead)

    return new_leads, duplicate_leads
