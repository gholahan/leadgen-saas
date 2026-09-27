# from typing import Any

# from httpx import AsyncClient, Timeout

# from app.core.config import settings
# from app.modules.enrichment.providers.base import EnrichmentProvider
# from app.modules.enrichment.schema import EnrichmentResult


# class HunterProvider(EnrichmentProvider):
#     def __init__(self, api_key: str | None = None):
#         self.api_key = api_key or settings.HUNTER_API_KEY
#         self.base_url = "https://api.hunter.io/v2"

#     async def enrich(self, domain: str, company_name: str | None = None) -> EnrichmentResult:
#         if not self.api_key:
#             return EnrichmentResult(status="FAILED")

#         url = f"{self.base_url}/domain_search"
#         params = {"domain": domain, "api_key": self.api_key}

#         async with AsyncClient(timeout=Timeout(15.0)) as client:
#             response = await client.get(url, params=params)
#             data = response.json()

#         if data.get("status") != "ok":
#             return EnrichmentResult(status="FAILED", raw_response=data)

#         results = data.get("data", {}).get("results", [])
#         if not results:
#             return EnrichmentResult(status="NOT_FOUND", domain=domain, raw_response=data)

#         first = results[0]
#         email = first.get("email")
#         email_type = first.get("type")
#         email_score = first.get("score")

#         return EnrichmentResult(
#             email=email,
#             email_type=email_type,
#             email_score=email_score,
#             domain=domain,
#             status="FOUND" if email else "NOT_FOUND",
#             raw_response=data,
#         )
