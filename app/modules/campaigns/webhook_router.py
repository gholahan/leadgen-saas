import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Request

from app.database.session import SessionDep
from app.modules.campaigns.webhook import (
    BrevoWebhookPayload,
    process_brevo_webhook_event,
    verify_brevo_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/brevo/email")
async def handle_brevo_email_webhook(
    request: Request,
    session: SessionDep,
    x_brevo_signature: str | None = Header(None),
):
    """
    Handle Brevo email delivery webhooks.

    Expected header: X-Brevo-Signature (HMAC-SHA256 hex digest)
    """
    body = await request.body()

    if x_brevo_signature:
        if not verify_brevo_webhook_signature(body, x_brevo_signature):
            logger.warning("Invalid Brevo webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    else:
        logger.warning("Missing Brevo webhook signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        payload = BrevoWebhookPayload.model_validate_json(body)
    except ValueError as exc:
        logger.error("Failed to parse Brevo webhook payload: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid payload")

    try:
        await process_brevo_webhook_event(payload, session)
    except Exception as exc:
        logger.exception("Error processing Brevo webhook: %s", exc)
        raise HTTPException(status_code=500, detail="Processing failed")

    return {"status": "received"}
