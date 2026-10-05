import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx

from app.modules.campaigns.model import CampaignStatus
from app.modules.campaigns.tasks import (
    _record_task_failure,
    _send_via_brevo,
    send_campaign_task,
)


class CampaignTaskTests(unittest.IsolatedAsyncioTestCase):
    def test_campaign_task_accepts_single_campaign_id_when_enqueued(self):
        task_id = str(uuid4())
        campaign_id = str(uuid4())

        with patch("app.core.celery.celery_app.send_task") as send_task:
            send_campaign_task.apply_async(args=[campaign_id], task_id=task_id)

        send_task.assert_called_once()
        self.assertEqual(send_task.call_args.args[1], [campaign_id])
        self.assertEqual(send_task.call_args.kwargs["task_id"], task_id)

    async def test_brevo_rate_limit_retries_using_retry_after(self):
        request = httpx.Request("POST", "https://api.brevo.com/v3/smtp/email")
        client = Mock(
            post=AsyncMock(
                side_effect=[
                    httpx.Response(429, headers={"Retry-After": "0"}, request=request),
                    httpx.Response(201, json={"messageId": "msg-123"}, request=request),
                ]
            )
        )

        with (
            patch("app.modules.campaigns.tasks.settings.BREVO_API_KEY", "test-key"),
            patch("app.modules.campaigns.tasks.asyncio.sleep", new_callable=AsyncMock) as sleep,
            self.assertLogs("app.modules.campaigns.tasks", level="INFO") as logs,
        ):
            message_id = await _send_via_brevo(
                from_email="sender@example.com",
                to="recipient@example.com",
                subject="Hello",
                html="<p>Hi</p>",
                client=client,
            )

        self.assertEqual(message_id, "msg-123")
        self.assertEqual(client.post.await_count, 2)
        sleep.assert_awaited_once_with(0.0)
        self.assertTrue(any("Brevo rate-limited email" in message for message in logs.output))
        self.assertTrue(any("Brevo accepted email (HTTP 201)" in message for message in logs.output))
        self.assertTrue(
            any(
                "Sending Brevo email payload" in message
                and "'subject': 'Hello'" in message
                and "'htmlContent': '<p>Hi</p>'" in message
                for message in logs.output
            )
        )
        self.assertEqual(
            client.post.await_args_list[-1].kwargs["json"],
            {
                "sender": {"email": "sender@example.com"},
                "to": [{"email": "recipient@example.com"}],
                "subject": "Hello",
                "htmlContent": "<p>Hi</p>",
                "textContent": "Hi",
            },
        )

    async def test_brevo_error_includes_provider_response(self):
        request = httpx.Request("POST", "https://api.brevo.com/v3/smtp/email")
        client = Mock(
            post=AsyncMock(
                return_value=httpx.Response(
                    400,
                    json={"code": "invalid_parameter", "message": "Invalid sender"},
                    request=request,
                )
            )
        )

        with patch("app.modules.campaigns.tasks.settings.BREVO_API_KEY", "test-key"):
            with self.assertRaisesRegex(RuntimeError, "Invalid sender"):
                await _send_via_brevo(
                    from_email="sender@example.com",
                    to="recipient@example.com",
                    subject="Hello",
                    html="<p>Hi</p>",
                    client=client,
                )

    async def test_uncaught_worker_error_marks_campaign_failed(self):
        campaign_id = uuid4()
        session = AsyncMock()
        session_factory = Mock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.modules.campaigns.tasks.make_celery_engine", return_value=object()),
            patch("app.modules.campaigns.tasks.AsyncSession", session_factory),
            patch(
                "app.modules.campaigns.tasks.get_campaign",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        status=CampaignStatus.RUNNING,
                        cancel_requested=False,
                    )
                ),
            ),
            patch(
                "app.modules.campaigns.tasks.update_campaign_status",
                new=AsyncMock(),
            ) as update_status,
        ):
            await _record_task_failure(str(campaign_id))

        update_status.assert_awaited_once_with(
            campaign_id,
            CampaignStatus.FAILED,
            session,
        )

    async def test_requested_cancel_is_preserved_on_worker_termination(self):
        campaign_id = uuid4()
        session = AsyncMock()
        session_factory = Mock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.modules.campaigns.tasks.make_celery_engine", return_value=object()),
            patch("app.modules.campaigns.tasks.AsyncSession", session_factory),
            patch(
                "app.modules.campaigns.tasks.get_campaign",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        status=CampaignStatus.RUNNING,
                        cancel_requested=True,
                    )
                ),
            ),
            patch(
                "app.modules.campaigns.tasks.update_campaign_status",
                new=AsyncMock(),
            ) as update_status,
        ):
            await _record_task_failure(str(campaign_id), terminated=True)

        update_status.assert_awaited_once_with(
            campaign_id,
            CampaignStatus.CANCELLED,
            session,
        )


if __name__ == "__main__":
    unittest.main()
