import asyncio
from typing import Any

from httpx import AsyncClient, Timeout

from app.core.config import settings
from app.modules.enrichment.providers.base import EnrichmentProvider
from app.modules.enrichment.schema import EnrichmentResult


class ProspeoProvider(EnrichmentProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.PROSPEO_API_KEY
        self.base_url = "https://api.prospeo.io"

    async def _post_with_rate_limit_retry(
        self,
        client: AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ):
        for attempt in range(3):
            response = await client.post(url, headers=headers, json=payload)
            if getattr(response, "status_code", 200) != 429 or attempt == 2:
                return response

            retry_after = response.headers.get("Retry-After")
            try:
                delay = min(max(float(retry_after), 0), 30)
            except (TypeError, ValueError):
                delay = 2**attempt
            await asyncio.sleep(delay)

        raise RuntimeError("Prospeo retry loop exited unexpectedly")

    async def _do_enrich(
        self,
        client: AsyncClient,
        domain: str,
        company_name: str | None,
        headers: dict[str, str],
    ) -> EnrichmentResult:
        """Core enrichment logic, runs against a caller-supplied HTTP client."""
        filters: dict[str, Any] = {"company": {}}
        if domain:
            filters["company"]["websites"] = {"include": [domain]}
        elif company_name:
            filters["company"]["names"] = {"include": [company_name]}

        search_response = await self._post_with_rate_limit_retry(
            client,
            f"{self.base_url}/search-person",
            headers,
            {"page": 1, "filters": filters},
        )
        search_result = search_response.json()

        if search_result.get("error"):
            return EnrichmentResult(
                status=(
                    "NOT_FOUND"
                    if search_result.get("error_code") == "NO_RESULTS"
                    else "FAILED"
                ),
                domain=domain,
            )

        results = search_result.get("results", [])
        if not results:
            return EnrichmentResult(status="NOT_FOUND", domain=domain)

        person_ids = [
            item["person"]["person_id"]
            for item in results
            if item.get("person", {}).get("person_id")
        ]
        if not person_ids:
            return EnrichmentResult(status="NOT_FOUND", domain=domain)

        async def _enrich_person(person_id: str) -> dict | None:
            resp = await self._post_with_rate_limit_retry(
                client,
                f"{self.base_url}/enrich-person",
                headers,
                {"data": {"person_id": person_id}, "only_verified_email": True},
            )
            return resp.json()

        enrich_results = await asyncio.gather(*(_enrich_person(pid) for pid in person_ids))

        for enrich_result in enrich_results:
            if enrich_result.get("error"):
                error_code = enrich_result.get("error_code")
                if error_code not in {"NO_MATCH", "NO_RESULTS"}:
                    return EnrichmentResult(status="FAILED", domain=domain)
                continue

            person = enrich_result.get("person") or {}
            email_data = person.get("email")
            if isinstance(email_data, dict):
                email = email_data.get("email") if email_data.get("revealed") else None
                email_type = email_data.get("status")
            else:
                email = email_data if isinstance(email_data, str) else None
                email_type = None

            if email:
                return EnrichmentResult(
                    email=email,
                    email_type=email_type,
                    domain=domain,
                    first_name=person.get("first_name") or None,
                    status="FOUND",
                )

        return EnrichmentResult(domain=domain, status="NOT_FOUND")

    async def enrich(
        self,
        domain: str,
        company_name: str | None = None,
        client: AsyncClient | None = None,
    ) -> EnrichmentResult:
        if not self.api_key:
            return EnrichmentResult(status="FAILED")

        if not domain and not company_name:
            return EnrichmentResult(status="FAILED")

        headers = {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        if client is not None:
            # Reuse the caller's shared connection pool (no TLS handshake cost)
            return await self._do_enrich(client, domain, company_name, headers)

        # Fallback: create a one-shot client (e.g. when called standalone)
        async with AsyncClient(timeout=Timeout(20.0)) as _client:
            return await self._do_enrich(_client, domain, company_name, headers)
