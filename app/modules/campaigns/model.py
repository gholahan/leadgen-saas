from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    __table_args__ = (Index("idx_campaigns_user_id", "user_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    name: str = Field(sa_column=Column(Text, nullable=False))
    status: CampaignStatus = Field(
        default=CampaignStatus.DRAFT,
        sa_column=Column(SAEnum(CampaignStatus, name="campaign_status"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


class CampaignLead(SQLModel, table=True):
    __tablename__ = "campaign_leads"

    campaign_id: UUID = Field(primary_key=True, foreign_key="campaigns.id", ondelete="CASCADE")
    lead_id: UUID = Field(primary_key=True, foreign_key="leads.id", ondelete="CASCADE")