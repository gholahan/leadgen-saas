import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import phonenumbers
from phonenumbers import PhoneNumberFormat

from app.modules.leads.model import Lead


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "ref",
    "source",
    "mc_cid",
    "mc_eid",
}

GENERIC_DOMAINS = {
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "linktr.ee",
    "wa.me",
    "whatsapp.com",
    "google.com",
    "maps.google.com",
    "goo.gl",
    "bit.ly",
    "t.co",
    "youtube.com",
    "tiktok.com",
    "pinterest.com",
}


def normalize_company_name(name: str | None) -> str | None:
    """Clean and standardize company name.

    - Strips emojis and control characters
    - Trims excess whitespace
    - Removes common Google Maps title-stuffing suffixes (e.g. '| Best Tech in Town')
    - Fixes ALL-CAPS names while preserving short acronyms
    """
    if not name:
        return None

    cleaned = name.strip()

    # Remove title stuffing like "Company Name | Description..." or "Company Name - Subtitle"
    if " | " in cleaned:
        parts = cleaned.split(" | ")
        if len(parts[0].split()) >= 1:
            cleaned = parts[0].strip()

    # Strip emoji & non-ascii symbols except standard punctuation
    cleaned = re.sub(r"[^\w\s\-\.,&'()/@]+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned:
        return None

    # If ALL-CAPS, convert to Title Case, keeping known acronyms uppercase
    if cleaned.isupper() and len(cleaned) > 3:
        words = cleaned.split()
        title_cased = []
        for w in words:
            if len(w) <= 3 and w.isalpha():
                title_cased.append(w.upper())
            else:
                title_cased.append(w.capitalize())
        cleaned = " ".join(title_cased)

    return cleaned or None

    # If ALL-CAPS, convert to Title Case, keeping known acronyms uppercase
    if cleaned.isupper() and len(cleaned) > 3:
        words = cleaned.split()
        title_cased = []
        for w in words:
            if len(w) <= 3 and w.isalpha():
                title_cased.append(w.upper())
            else:
                title_cased.append(w.capitalize())
        cleaned = " ".join(title_cased)

    return cleaned or None


def extract_clean_domain(url: str | None) -> str | None:
    """Extract normalized root domain without www, subpaths, or ports."""
    if not url:
        return None

    url_str = url.strip()
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    try:
        parsed = urlparse(url_str)
        netloc = parsed.netloc.lower().split(":")[0]  # remove port
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc if netloc else None
    except Exception:
        return None


def is_generic_domain(domain: str | None) -> bool:
    """Check if domain is a generic social or link aggregator domain."""
    if not domain:
        return True
    return domain in GENERIC_DOMAINS or any(domain.endswith("." + g) for g in GENERIC_DOMAINS)


def normalize_website(url: str | None) -> str | None:
    """Standardize website URL.

    - Prepends https:// if missing
    - Lowercases scheme and host
    - Strips tracking query parameters (utm_*, fbclid, etc.)
    - Removes trailing slashes on bare domains
    """
    if not url:
        return None

    url_str = url.strip()
    if not url_str:
        return None

    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    try:
        parsed = urlparse(url_str)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Filter out tracking query parameters
        query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
        clean_query_tuples = [(k, v) for k, v in query_tuples if k.lower() not in TRACKING_PARAMS]
        clean_query = urlencode(clean_query_tuples)

        path = parsed.path
        if path == "/":
            path = ""

        clean_url = urlunparse((scheme, netloc, path, parsed.params, clean_query, ""))
        return clean_url.rstrip("/") if not clean_query and not path else clean_url
    except Exception:
        return url_str


def normalize_phone(phone: str | None, default_country: str | None = None) -> str | None:
    """Standardize phone numbers to E.164 format (+12345678900).

    Uses phonenumbers library with country code hint.
    Falls back to cleaned digits if unparseable.
    """
    if not phone:
        return None

    phone_str = phone.strip()
    if not phone_str:
        return None

    country_hint = (default_country.upper() if default_country and len(default_country) == 2 else None)

    try:
        parsed_num = phonenumbers.parse(phone_str, country_hint)
        if phonenumbers.is_possible_number(parsed_num):
            return phonenumbers.format_number(parsed_num, PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    # Fallback: clean string, keep leading + if present
    has_plus = phone_str.startswith("+")
    digits = re.sub(r"\D", "", phone_str)
    if digits:
        return f"+{digits}" if has_plus else digits

    return None


def normalize_email(email: str | None) -> str | None:
    """Standardize email address (lowercase, trim)."""
    if not email:
        return None

    cleaned = email.strip().lower()
    # Simple regex check for reasonable email shape
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
        return cleaned
    return None


def normalize_country(country: str | None) -> str | None:
    """Standardize country code to 2-letter ISO uppercase."""
    if not country:
        return None
    cleaned = country.strip().upper()
    return cleaned if len(cleaned) == 2 else cleaned


def normalize_lead(lead: Lead) -> Lead:
    """Normalize all fields of a single Lead instance in-place."""
    country_code = normalize_country(lead.country)

    lead.company_name = normalize_company_name(lead.company_name) or lead.company_name
    lead.website = normalize_website(lead.website)
    lead.phone = normalize_phone(lead.phone, default_country=country_code)
    lead.email = normalize_email(lead.email)
    lead.country = country_code
    lead.city = lead.city.strip().title() if lead.city else None
    lead.state = lead.state.strip() if lead.state else None
    lead.address = re.sub(r"\s+", " ", lead.address.strip()) if lead.address else None
    lead.industry = lead.industry.strip() if lead.industry else None

    return lead


def normalize_leads(leads: list[Lead]) -> list[Lead]:
    """Normalize a batch of leads."""
    return [normalize_lead(lead) for lead in leads]
