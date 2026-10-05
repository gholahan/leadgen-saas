import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.modules.campaigns.model import CampaignStatus
from app.modules.jobs.model import JobStatus
from app.modules.campaigns.service import start_campaign


class CampaignServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_persists_state_before_dispatching_task(self):
        campaign_id = uuid4()
        user_id = uuid4()
        job_id = uuid4()
        campaign = SimpleNamespace(
            user_id=user_id,
            job_id=job_id,
            status=CampaignStatus.DRAFT,
        )
        events = []

        async def persist_task_id(campaign_id_arg, task_id, session):
            events.append(("persist", task_id))
            return True

        def dispatch(args, task_id):
            events.append(("dispatch", task_id))

        fake_task = SimpleNamespace(apply_async=Mock(side_effect=dispatch))
        session = AsyncMock()

        with (
            patch(
                "app.modules.campaigns.service.get_campaign",
                new=AsyncMock(return_value=campaign),
            ),
            patch(
                "app.modules.campaigns.service.get_job_by_id",
                new=AsyncMock(return_value=SimpleNamespace(status=JobStatus.COMPLETED)),
            ),
            patch(
                "app.modules.campaigns.service.set_campaign_task_id",
                new=AsyncMock(side_effect=persist_task_id),
            ),
            patch(
                "app.modules.campaigns.tasks.send_campaign_task",
                fake_task,
            ),
        ):
            await start_campaign(campaign_id, user_id, session)

        self.assertEqual([event[0] for event in events], ["persist", "dispatch"])
        self.assertEqual(events[0][1], events[1][1])
        fake_task.apply_async.assert_called_once_with(
            args=[str(campaign_id)], task_id=events[0][1]
        )

    async def test_start_rejects_campaign_for_failed_job(self):
        campaign_id = uuid4()
        user_id = uuid4()
        campaign = SimpleNamespace(
            user_id=user_id,
            job_id=uuid4(),
            status=CampaignStatus.DRAFT,
        )

        with (
            patch(
                "app.modules.campaigns.service.get_campaign",
                new=AsyncMock(return_value=campaign),
            ),
            patch(
                "app.modules.campaigns.service.get_job_by_id",
                new=AsyncMock(return_value=SimpleNamespace(status=JobStatus.FAILED)),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "after its job has completed"):
                await start_campaign(campaign_id, user_id, AsyncMock())


if __name__ == "__main__":
    unittest.main()
