import hashlib
import hmac
import logging
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.modules.campaigns.model import CampaignRecipient, EmailEvent, EmailEventType

logger = logging.getLogger(__name__)


class BrevoWebhookPayload(BaseModel):
    """Schema for Brevo webhook events."""

    event: str = Field(
        ..., description="Event type: 'delivered', 'bounce', 'opened', 'clicked', 'complaint'"
    )
    messageId: str = Field(..., description="Brevo message ID (provider_message_id)")
    email: str = Field(..., description="Recipient email address")
    ts_event: int = Field(..., description="Unix timestamp of the event")
    bounce: str | None = Field(default=None, description="Bounce type: 'hard' or 'soft'")

    model_config = {"extra": "allow"}


def verify_brevo_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Brevo webhook signature using HMAC-SHA256."""
    if not settings.BREVO_WEBHOOK_SECRET:
        logger.warning("BREVO_WEBHOOK_SECRET not configured; skipping webhook verification")
        return False

    expected_signature = hmac.new(
        settings.BREVO_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


async def find_recipient_by_message_id(
    provider_message_id: str, session: AsyncSession
) -> dict | None:
    """Find a campaign recipient by Brevo message ID.
    
    Returns a dict with 'id' and 'email', or None if not found.
    Uses raw SQL to avoid ORM hydration issues in tests.
    """
    result = await session.exec(
        sa.text("""
            SELECT id, email FROM campaign_recipients 
            WHERE provider_message_id = :provider_message_id
        """).bindparams(provider_message_id=provider_message_id)
    )
    row = result.first()
    if row:
        return {"id": row[0], "email": row[1]}
    return None


async def handle_delivered_event(
    recipient: dict,
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Record email delivery event."""
    event_dt = datetime.fromtimestamp(payload.ts_event, tz=timezone.utc)
    
    # Update recipient with raw SQL to avoid ORM issues
    await session.exec(sa.text("""
        UPDATE campaign_recipients
        SET delivered_at = :delivered_at
        WHERE id = :id AND delivered_at IS NULL
    """).bindparams(
        delivered_at=event_dt,
        id=recipient["id"],
    ))

    # Create event with raw SQL
    event_id = UUID(__import__('uuid').uuid4().hex)
    provider_event_id = f"{payload.messageId}-delivered-{payload.ts_event}"
    await session.exec(sa.text("""
        INSERT INTO email_events
        (id, campaign_recipient_id, event_type, provider_event_id, event_timestamp, created_at)
        VALUES (:id, :campaign_recipient_id, :event_type, :provider_event_id, :event_timestamp, :created_at)
    """).bindparams(
        id=str(event_id),
        campaign_recipient_id=recipient["id"],
        event_type="DELIVERED",
        provider_event_id=provider_event_id,
        event_timestamp=event_dt,
        created_at=datetime.now(timezone.utc),
    ))
    
    logger.info(
        "Recorded delivery event for recipient %s (%s)",
        recipient["id"],
        recipient["email"],
    )


async def handle_bounce_event(
    recipient: dict,
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Record email bounce event."""
    event_dt = datetime.fromtimestamp(payload.ts_event, tz=timezone.utc)
    bounce_type = payload.bounce or "unknown"
    
    await session.exec(sa.text("""
        UPDATE campaign_recipients
        SET bounced_at = :bounced_at, bounce_type = :bounce_type
        WHERE id = :id AND bounced_at IS NULL
    """).bindparams(
        bounced_at=event_dt,
        bounce_type=bounce_type,
        id=recipient["id"],
    ))

    event_id = UUID(__import__('uuid').uuid4().hex)
    provider_event_id = f"{payload.messageId}-bounced-{payload.ts_event}"
    await session.exec(sa.text("""
        INSERT INTO email_events
        (id, campaign_recipient_id, event_type, provider_event_id, event_timestamp, created_at)
        VALUES (:id, :campaign_recipient_id, :event_type, :provider_event_id, :event_timestamp, :created_at)
    """).bindparams(
        id=str(event_id),
        campaign_recipient_id=recipient["id"],
        event_type="BOUNCED",
        provider_event_id=provider_event_id,
        event_timestamp=event_dt,
        created_at=datetime.now(timezone.utc),
    ))

    logger.info(
        "Recorded bounce event for recipient %s (%s): %s",
        recipient["id"],
        recipient["email"],
        bounce_type,
    )


async def handle_opened_event(
    recipient: dict,
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Record email open event."""
    event_dt = datetime.fromtimestamp(payload.ts_event, tz=timezone.utc)
    
    await session.exec(sa.text("""
        UPDATE campaign_recipients
        SET opened_at = :opened_at
        WHERE id = :id AND opened_at IS NULL
    """).bindparams(
        opened_at=event_dt,
        id=recipient["id"],
    ))

    event_id = UUID(__import__('uuid').uuid4().hex)
    provider_event_id = f"{payload.messageId}-opened-{payload.ts_event}"
    await session.exec(sa.text("""
        INSERT INTO email_events
        (id, campaign_recipient_id, event_type, provider_event_id, event_timestamp, created_at)
        VALUES (:id, :campaign_recipient_id, :event_type, :provider_event_id, :event_timestamp, :created_at)
    """).bindparams(
        id=str(event_id),
        campaign_recipient_id=recipient["id"],
        event_type="OPENED",
        provider_event_id=provider_event_id,
        event_timestamp=event_dt,
        created_at=datetime.now(timezone.utc),
    ))

    logger.info(
        "Recorded open event for recipient %s (%s)",
        recipient["id"],
        recipient["email"],
    )


async def handle_clicked_event(
    recipient: dict,
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Record email link click event."""
    event_dt = datetime.fromtimestamp(payload.ts_event, tz=timezone.utc)
    
    await session.exec(sa.text("""
        UPDATE campaign_recipients
        SET clicked_at = :clicked_at
        WHERE id = :id AND clicked_at IS NULL
    """).bindparams(
        clicked_at=event_dt,
        id=recipient["id"],
    ))

    event_id = UUID(__import__('uuid').uuid4().hex)
    provider_event_id = f"{payload.messageId}-clicked-{payload.ts_event}"
    await session.exec(sa.text("""
        INSERT INTO email_events
        (id, campaign_recipient_id, event_type, provider_event_id, event_timestamp, created_at)
        VALUES (:id, :campaign_recipient_id, :event_type, :provider_event_id, :event_timestamp, :created_at)
    """).bindparams(
        id=str(event_id),
        campaign_recipient_id=recipient["id"],
        event_type="CLICKED",
        provider_event_id=provider_event_id,
        event_timestamp=event_dt,
        created_at=datetime.now(timezone.utc),
    ))

    logger.info(
        "Recorded click event for recipient %s (%s)",
        recipient["id"],
        recipient["email"],
    )


async def handle_complained_event(
    recipient: dict,
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Record spam complaint event."""
    event_dt = datetime.fromtimestamp(payload.ts_event, tz=timezone.utc)
    
    await session.exec(sa.text("""
        UPDATE campaign_recipients
        SET complained_at = :complained_at
        WHERE id = :id AND complained_at IS NULL
    """).bindparams(
        complained_at=event_dt,
        id=recipient["id"],
    ))

    event_id = UUID(__import__('uuid').uuid4().hex)
    provider_event_id = f"{payload.messageId}-complained-{payload.ts_event}"
    await session.exec(sa.text("""
        INSERT INTO email_events
        (id, campaign_recipient_id, event_type, provider_event_id, event_timestamp, created_at)
        VALUES (:id, :campaign_recipient_id, :event_type, :provider_event_id, :event_timestamp, :created_at)
    """).bindparams(
        id=str(event_id),
        campaign_recipient_id=recipient["id"],
        event_type="COMPLAINED",
        provider_event_id=provider_event_id,
        event_timestamp=event_dt,
        created_at=datetime.now(timezone.utc),
    ))

    logger.info(
        "Recorded complaint event for recipient %s (%s)",
        recipient["id"],
        recipient["email"],
    )


EVENT_HANDLERS = {
    "delivered": handle_delivered_event,
    "bounce": handle_bounce_event,
    "opened": handle_opened_event,
    "clicked": handle_clicked_event,
    "complaint": handle_complained_event,
}


async def process_brevo_webhook_event(
    payload: BrevoWebhookPayload,
    session: AsyncSession,
) -> None:
    """Process a Brevo webhook event and update the database."""
    handler = EVENT_HANDLERS.get(payload.event)
    if not handler:
        logger.warning("Unsupported webhook event type: %s", payload.event)
        return

    recipient = await find_recipient_by_message_id(payload.messageId, session)
    if not recipient:
        logger.warning(
            "Recipient not found for message ID %s (email: %s)",
            payload.messageId,
            payload.email,
        )
        return

    try:
        await handler(recipient, payload, session)
        await session.commit()
    except sa.exc.IntegrityError as exc:
        # Duplicate event (provider_event_id already exists) - log and continue
        await session.rollback()
        if "UNIQUE constraint failed" in str(exc) or "provider_event_id" in str(exc):
            logger.info(
                "Duplicate webhook event for message %s (provider_event_id already recorded)",
                payload.messageId,
            )
        else:
            logger.exception(
                "IntegrityError processing webhook event for message %s: %s",
                payload.messageId,
                exc,
            )
            raise
    except Exception as exc:
        await session.rollback()
        logger.exception(
            "Error processing webhook event for message %s: %s",
            payload.messageId,
            exc,
        )
        raise
