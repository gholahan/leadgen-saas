import asyncio
import unittest
from unittest.mock import patch

from app.modules.enrichment.providers import prospeo as prospeo_module
from app.modules.enrichment.providers.prospeo import ProspeoProvider


class FakeResponse:
    def __init__(self, body, status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.body


class FakeAsyncClient:
    responses = []
    calls = []

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, tuple):
            status_code, headers, body = response
            return FakeResponse(body, status_code, headers)
        return FakeResponse(response)


class ProspeoProviderTests(unittest.TestCase):
    def run_provider(self, responses):
        FakeAsyncClient.responses = list(responses)
        FakeAsyncClient.calls = []
        with patch.object(prospeo_module, "AsyncClient", FakeAsyncClient):
            result = asyncio.run(
                ProspeoProvider(api_key="test-key").enrich(
                    "example.com", "Example Company"
                )
            )
        return result

    def test_searches_company_then_enriches_person_id(self):
        result = self.run_provider(
            [
                {
                    "error": False,
                    "results": [{"person": {"person_id": "person-123"}}],
                },
                {
                    "error": False,
                    "person": {
                        "email": {
                            "status": "VERIFIED",
                            "revealed": True,
                            "email": "ceo@example.com",
                        }
                    },
                },
            ]
        )

        self.assertEqual(result.status, "FOUND")
        self.assertEqual(result.email, "ceo@example.com")
        self.assertEqual(result.email_type, "VERIFIED")
        self.assertEqual(len(FakeAsyncClient.calls), 2)

        search_url, search_request = FakeAsyncClient.calls[0]
        self.assertEqual(search_url, "https://api.prospeo.io/search-person")
        self.assertEqual(search_request["headers"]["X-KEY"], "test-key")
        self.assertEqual(
            search_request["json"]["filters"]["company"]["websites"]["include"],
            ["example.com"],
        )

        enrich_url, enrich_request = FakeAsyncClient.calls[1]
        self.assertEqual(enrich_url, "https://api.prospeo.io/enrich-person")
        self.assertEqual(enrich_request["json"]["data"], {"person_id": "person-123"})

    def test_does_not_return_unrevealed_email(self):
        result = self.run_provider(
            [
                {
                    "error": False,
                    "results": [{"person": {"person_id": "person-123"}}],
                },
                {
                    "error": False,
                    "person": {
                        "email": {
                            "status": "VERIFIED",
                            "revealed": False,
                            "email": "c**@example.com",
                        }
                    },
                },
            ]
        )

        self.assertEqual(result.status, "NOT_FOUND")
        self.assertIsNone(result.email)

    def test_continues_to_next_person_when_first_has_no_email(self):
        result = self.run_provider(
            [
                {
                    "error": False,
                    "results": [
                        {"person": {"person_id": "person-123"}},
                        {"person": {"person_id": "person-456"}},
                    ],
                },
                {
                    "error": False,
                    "person": {"email": {"revealed": False, "status": "VERIFIED"}},
                },
                {
                    "error": False,
                    "person": {
                        "email": {
                            "revealed": True,
                            "status": "VERIFIED",
                            "email": "second@example.com",
                        }
                    },
                },
            ]
        )

        self.assertEqual(result.status, "FOUND")
        self.assertEqual(result.email, "second@example.com")
        self.assertEqual(len(FakeAsyncClient.calls), 3)

    def test_returns_not_found_when_company_has_no_people(self):
        result = self.run_provider([{"error": False, "results": []}])

        self.assertEqual(result.status, "NOT_FOUND")
        self.assertEqual(len(FakeAsyncClient.calls), 1)

    def test_retries_rate_limit_using_retry_after(self):
        result = self.run_provider(
            [
                {
                    "error": False,
                    "results": [{"person": {"person_id": "person-123"}}],
                },
                (
                    429,
                    {"Retry-After": "0"},
                    {"error": True, "error_code": "Rate limit exceeded"},
                ),
                {
                    "error": False,
                    "person": {
                        "email": {
                            "status": "VERIFIED",
                            "revealed": True,
                            "email": "ceo@example.com",
                        }
                    },
                },
            ]
        )

        self.assertEqual(result.status, "FOUND")
        self.assertEqual(result.email, "ceo@example.com")
        self.assertEqual(len(FakeAsyncClient.calls), 3)

    def test_search_no_results_is_not_found_not_failed(self):
        result = self.run_provider(
            [{"error": True, "error_code": "NO_RESULTS"}]
        )

        self.assertEqual(result.status, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()