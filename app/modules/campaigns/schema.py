from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.modules.campaigns.model import CampaignStatus, RecipientStatus, EmailEventType


class CampaignCreate(BaseModel):
    job_id: UUID
    subject: str
    body: str
    from_email: str | None = None


class CampaignResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    subject: str
    body: str
    from_email: str | None
    status: CampaignStatus
    cancel_requested: bool
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class EmailEventResponse(BaseModel):
    id: UUID
    campaign_recipient_id: UUID
    event_type: EmailEventType
    provider_event_id: str | None
    event_timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipientResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    lead_id: UUID
    enrichment_id: UUID
    email: str
    first_name: str | None
    status: RecipientStatus
    provider_message_id: str | None
    error_message: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    bounced_at: datetime | None
    bounce_type: str | None
    opened_at: datetime | None
    clicked_at: datetime | None
    complained_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
