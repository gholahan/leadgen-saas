from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.modules.campaigns.model import CampaignStatus, RecipientStatus


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
    created_at: datetime

    model_config = {"from_attributes": True}
