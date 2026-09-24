from urllib.parse import parse_qs, urlparse


def extract_place_id(google_maps_url: str | None) -> str | None:
    if not google_maps_url:
        return None

    parsed = urlparse(google_maps_url)
    query = parse_qs(parsed.query)

    place_query = query.get("q", [None])[0]

    if not place_query:
        return None

    if place_query.startswith("place_id:"):
        return place_query.removeprefix("place_id:")

    return None
