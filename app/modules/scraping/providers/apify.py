from apify_client import ApifyClientAsync

from app.core.config import settings


class ApifyProvider:

    def __init__(self):
        self.client = ApifyClientAsync(settings.APIFY_API_KEY)

    async def scrape_businesses(
        self,
        industry: str,
        location: str,
        target_count: int,
    ) -> list[dict]:

        run_input = {
            "enrichContacts": False,
            "fullCoverage": False,
            "locations": [location],
            "maxCrawledPlacesPerSearch": 0,
            "maxPlacesPerSearch": target_count,
            "onlyNew": False,
            "onlyWithEmail": False,
            "proxyConfiguration": {
                "useApifyProxy": True,
            },
            "searches": [industry],
            "skipClosed": False,
            "withinRadiusOnly": False,
        }

        actor = self.client.actor("kestrel/google-maps-scraper")

        run = await actor.call(
            run_input=run_input
        )

        dataset = self.client.dataset(
            run.default_dataset_id
        )

        result = await dataset.list_items(
            limit=target_count
        )

        return result.items