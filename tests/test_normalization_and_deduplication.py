import uuid
from decimal import Decimal
from app.modules.leads.model import Lead
from app.modules.normalization.service import (
    extract_clean_domain,
    is_generic_domain,
    normalize_company_name,
    normalize_country,
    normalize_email,
    normalize_lead,
    normalize_leads,
    normalize_phone,
    normalize_website,
)
from app.modules.deduplication.service import deduplicate_leads


def test_normalize_company_name():
    # Title stuffing removal
    assert normalize_company_name("Acme Corp | Best Plumbers in Town") == "Acme Corp"
    assert normalize_company_name("  Fintrak Software   Company Limited  ") == "Fintrak Software Company Limited"
    # ALL-CAPS fixing with acronym preservation
    assert normalize_company_name("FINTECH SOFTWARE SOLUTIONS AI") == "Fintech Software Solutions AI"
    # Emoji / symbol stripping
    assert normalize_company_name("🚀 Super Movers & Co. 🌟") == "Super Movers & Co."


def test_normalize_website_and_domain():
    # Stripping UTM and query parameters
    assert normalize_website("http://example.com/?utm_source=google&utm_medium=cpc") == "http://example.com"
    assert normalize_website("www.acme.com/about/") == "https://www.acme.com/about/"
    assert extract_clean_domain("https://www.example.com:8080/path?q=1") == "example.com"
    assert extract_clean_domain("http://sub.domain.co.uk/") == "sub.domain.co.uk"
    assert is_generic_domain("facebook.com") is True
    assert is_generic_domain("instagram.com") is True
    assert is_generic_domain("mysite.com") is False


def test_normalize_phone():
    # Nigerian number format
    assert normalize_phone("+234 802 900 8672") == "+2348029008672"
    # US number format with country hint
    assert normalize_phone("(555) 234-5678", default_country="US") == "+15552345678"
    assert normalize_phone("+1-800-555-0199") == "+18005550199"


def test_normalize_country_and_email():
    assert normalize_country("ng") == "NG"
    assert normalize_email("  Test.User@Example.COM  ") == "test.user@example.com"
    assert normalize_email("invalid-email") is None


def test_deduplication_by_place_id():
    job_id = uuid.uuid4()
    lead1 = Lead(
        job_id=job_id,
        company_name="Apex Tech",
        place_id="ChIJ12345",
        phone="+1234567890",
        rating=Decimal("4.5"),
        review_count=10,
    )
    lead2 = Lead(
        job_id=job_id,
        company_name="Apex Technologies Inc",
        place_id="ChIJ12345",  # Same place_id
        website="https://apextech.io",
        email="info@apextech.io",
        rating=Decimal("4.8"),
        review_count=25,  # Richer review count
    )

    deduped = deduplicate_leads([lead1, lead2])
    assert len(deduped) == 1
    survivor = deduped[0]
    # Verify merging enriched missing fields
    assert survivor.website == "https://apextech.io"
    assert survivor.email == "info@apextech.io"
    assert survivor.phone == "+1234567890"
    assert survivor.review_count == 25
    assert survivor.rating == Decimal("4.8")


def test_deduplication_by_domain():
    job_id = uuid.uuid4()
    lead1 = Lead(
        job_id=job_id,
        company_name="Alpha Software",
        website="https://alphasoftware.com/contact",
    )
    lead2 = Lead(
        job_id=job_id,
        company_name="Alpha Soft",
        website="https://www.alphasoftware.com/?utm_source=fb",
        phone="+1987654321",
    )

    normalized = normalize_leads([lead1, lead2])
    deduped = deduplicate_leads(normalized)
    assert len(deduped) == 1
    assert deduped[0].phone == "+1987654321"


def test_deduplication_generic_domains_not_merged():
    # Two different companies with Facebook URLs should NOT be merged
    job_id = uuid.uuid4()
    lead1 = Lead(
        job_id=job_id,
        company_name="Bakery One",
        website="https://facebook.com/bakeryone",
        city="Chicago",
        country="US",
    )
    lead2 = Lead(
        job_id=job_id,
        company_name="Plumber Two",
        website="https://facebook.com/plumbertwo",
        city="Miami",
        country="US",
    )

    normalized = normalize_leads([lead1, lead2])
    deduped = deduplicate_leads(normalized)
    assert len(deduped) == 2
