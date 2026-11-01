import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, select

from app.modules.campaigns.model import (
    CampaignRecipient,
    RecipientStatus,
    EmailEvent,
    EmailEventType,
)
from app.modules.campaigns.webhook import (
    BrevoWebhookPayload,
    process_brevo_webhook_event,
    verify_brevo_webhook_signature,
    find_recipient_by_message_id,
)


class WebhookSignatureTests(unittest.IsolatedAsyncioTestCase):
    """Test Brevo webhook signature verification."""

    async def test_valid_signature_passes_verification(self):
        """Verify that a correctly signed payload passes verification."""
        secret = "test-webhook-secret"
        body = b'{"event":"delivered","messageId":"msg-123","ts_event":1696420800}'

        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        from unittest.mock import patch

        with patch("app.modules.campaigns.webhook.settings.BREVO_WEBHOOK_SECRET", secret):
            self.assertTrue(
                verify_brevo_webhook_signature(body, expected_signature)
            )

    async def test_invalid_signature_fails_verification(self):
        """Verify that an incorrectly signed payload fails verification."""
        secret = "test-webhook-secret"
        body = b'{"event":"delivered","messageId":"msg-123","ts_event":1696420800}'
        invalid_signature = "invalid_signature_here"

        from unittest.mock import patch

        with patch("app.modules.campaigns.webhook.settings.BREVO_WEBHOOK_SECRET", secret):
            self.assertFalse(
                verify_brevo_webhook_signature(body, invalid_signature)
            )

    async def test_missing_secret_returns_false(self):
        """Verify that missing webhook secret returns False (no verification)."""
        from unittest.mock import patch

        with patch("app.modules.campaigns.webhook.settings.BREVO_WEBHOOK_SECRET", None):
            self.assertFalse(
                verify_brevo_webhook_signature(b"body", "signature")
            )


class WebhookEventProcessingTests(unittest.IsolatedAsyncioTestCase):
    """Test webhook event processing."""

    async def asyncSetUp(self):
        """Set up in-memory SQLite database with minimal schema."""
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            echo=False,
        )

        # Create tables manually to avoid foreign key resolution issues
        async with self.engine.begin() as conn:
            await conn.execute(sa.text("""
                CREATE TABLE campaign_recipients (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    lead_id TEXT NOT NULL,
                    enrichment_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    first_name TEXT,
                    status TEXT NOT NULL,
                    provider_message_id TEXT,
                    error_message TEXT,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    bounced_at TIMESTAMP,
                    bounce_type TEXT,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    complained_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL
                )
            """))
            await conn.execute(sa.text("""
                CREATE TABLE email_events (
                    id TEXT PRIMARY KEY,
                    campaign_recipient_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    provider_event_id TEXT UNIQUE,
                    event_timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(campaign_recipient_id) REFERENCES campaign_recipients(id)
                )
            """))
            await conn.execute(sa.text("""
                CREATE INDEX idx_email_events_campaign_recipient_id 
                ON email_events(campaign_recipient_id)
            """))

        self.session = AsyncSession(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        """Clean up database."""
        await self.session.close()
        await self.engine.dispose()

    async def _create_recipient(self, recipient_id: str, message_id: str) -> None:
        """Helper to insert a recipient."""
        await self.session.exec(sa.text("""
            INSERT INTO campaign_recipients 
            (id, campaign_id, lead_id, enrichment_id, email, status, provider_message_id, created_at)
            VALUES (:id, :campaign_id, :lead_id, :enrichment_id, :email, :status, :provider_message_id, :created_at)
        """).bindparams(
            id=recipient_id,
            campaign_id=str(uuid4()),
            lead_id=str(uuid4()),
            enrichment_id=str(uuid4()),
            email="test@example.com",
            status="SENT",
            provider_message_id=message_id,
            created_at=datetime.now(timezone.utc),
        ))
        await self.session.commit()

    async def test_delivered_event_updates_recipient_and_creates_event(self):
        """Test that a DELIVERED event updates recipient and creates an event record."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="delivered",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
        )

        await process_brevo_webhook_event(payload, self.session)

        # Verify recipient was updated
        result = await self.session.exec(sa.text(
            "SELECT delivered_at FROM campaign_recipients WHERE id = :id"
        ).bindparams(id=recipient_id))
        row = result.first()
        self.assertIsNotNone(row[0])

        # Verify event was created
        event_result = await self.session.exec(sa.text(
            "SELECT COUNT(*) FROM email_events WHERE campaign_recipient_id = :id"
        ).bindparams(id=recipient_id))
        count = event_result.first()[0]
        self.assertEqual(count, 1)

    async def test_bounce_event_records_bounce_type(self):
        """Test that a BOUNCE event records bounce type."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="bounce",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
            bounce="hard",
        )

        await process_brevo_webhook_event(payload, self.session)

        result = await self.session.exec(sa.text(
            "SELECT bounced_at, bounce_type FROM campaign_recipients WHERE id = :id"
        ).bindparams(id=recipient_id))
        row = result.first()
        self.assertIsNotNone(row[0])
        self.assertEqual(row[1], "hard")

    async def test_opened_event_records_open_timestamp(self):
        """Test that an OPENED event records the open timestamp."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="opened",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
        )

        await process_brevo_webhook_event(payload, self.session)

        result = await self.session.exec(sa.text(
            "SELECT opened_at FROM campaign_recipients WHERE id = :id"
        ).bindparams(id=recipient_id))
        row = result.first()
        self.assertIsNotNone(row[0])

    async def test_clicked_event_records_click_timestamp(self):
        """Test that a CLICKED event records the click timestamp."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="clicked",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
        )

        await process_brevo_webhook_event(payload, self.session)

        result = await self.session.exec(sa.text(
            "SELECT clicked_at FROM campaign_recipients WHERE id = :id"
        ).bindparams(id=recipient_id))
        row = result.first()
        self.assertIsNotNone(row[0])

    async def test_complained_event_records_complaint_timestamp(self):
        """Test that a COMPLAINT event records the complaint timestamp."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="complaint",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
        )

        await process_brevo_webhook_event(payload, self.session)

        result = await self.session.exec(sa.text(
            "SELECT complained_at FROM campaign_recipients WHERE id = :id"
        ).bindparams(id=recipient_id))
        row = result.first()
        self.assertIsNotNone(row[0])

    async def test_duplicate_events_are_idempotent(self):
        """Test that duplicate events do not create multiple records."""
        recipient_id = str(uuid4())
        message_id = "msg-12345"
        await self._create_recipient(recipient_id, message_id)

        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="delivered",
            messageId=message_id,
            email="test@example.com",
            ts_event=ts_event,
        )

        # Process the same event twice
        await process_brevo_webhook_event(payload, self.session)
        await process_brevo_webhook_event(payload, self.session)

        event_result = await self.session.exec(sa.text(
            "SELECT COUNT(*) FROM email_events WHERE campaign_recipient_id = :id"
        ).bindparams(id=recipient_id))
        count = event_result.first()[0]
        # Duplicate events are ignored due to unique constraint (idempotency)
        self.assertEqual(count, 1)

    async def test_unknown_message_id_logs_warning_and_continues(self):
        """Test that unknown message IDs are logged and do not crash."""
        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="delivered",
            messageId="unknown-msg-id",
            email="test@example.com",
            ts_event=ts_event,
        )

        import logging

        with self.assertLogs("app.modules.campaigns.webhook", level="WARNING") as logs:
            await process_brevo_webhook_event(payload, self.session)

        self.assertTrue(
            any("Recipient not found" in msg for msg in logs.output)
        )

    async def test_unsupported_event_type_logs_warning_and_continues(self):
        """Test that unsupported event types are logged and do not crash."""
        ts_event = int(datetime.now(timezone.utc).timestamp())
        payload = BrevoWebhookPayload(
            event="unsupported_event",
            messageId="msg-12345",
            email="test@example.com",
            ts_event=ts_event,
        )

        import logging

        with self.assertLogs("app.modules.campaigns.webhook", level="WARNING") as logs:
            await process_brevo_webhook_event(payload, self.session)

        self.assertTrue(
            any("Unsupported webhook event type" in msg for msg in logs.output)
        )


class RecipientLookupTests(unittest.IsolatedAsyncioTestCase):
    """Test recipient lookup by message ID."""

    async def asyncSetUp(self):
        """Set up in-memory SQLite database."""
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            echo=False,
        )

        async with self.engine.begin() as conn:
            await conn.execute(sa.text("""
                CREATE TABLE campaign_recipients (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    lead_id TEXT NOT NULL,
                    enrichment_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    first_name TEXT,
                    status TEXT NOT NULL,
                    provider_message_id TEXT,
                    error_message TEXT,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    bounced_at TIMESTAMP,
                    bounce_type TEXT,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    complained_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL
                )
            """))
            await conn.execute(sa.text("""
                CREATE TABLE email_events (
                    id TEXT PRIMARY KEY,
                    campaign_recipient_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    provider_event_id TEXT UNIQUE,
                    event_timestamp TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """))

        self.session = AsyncSession(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        """Clean up database."""
        await self.session.close()
        await self.engine.dispose()

    async def test_find_recipient_by_message_id_returns_correct_recipient(self):
        """Test finding a recipient by message ID."""
        message_id = "msg-12345"
        recipient_id = str(uuid4())

        await self.session.exec(sa.text("""
            INSERT INTO campaign_recipients 
            (id, campaign_id, lead_id, enrichment_id, email, status, provider_message_id, created_at)
            VALUES (:id, :campaign_id, :lead_id, :enrichment_id, :email, :status, :provider_message_id, :created_at)
        """).bindparams(
            id=recipient_id,
            campaign_id=str(uuid4()),
            lead_id=str(uuid4()),
            enrichment_id=str(uuid4()),
            email="test@example.com",
            status="SENT",
            provider_message_id=message_id,
            created_at=datetime.now(timezone.utc),
        ))
        await self.session.commit()

        found = await find_recipient_by_message_id(message_id, self.session)
        self.assertIsNotNone(found)
        self.assertEqual(found["email"], "test@example.com")

    async def test_find_recipient_by_nonexistent_message_id_returns_none(self):
        """Test that looking up a non-existent message ID returns None."""
        found = await find_recipient_by_message_id("nonexistent", self.session)
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
