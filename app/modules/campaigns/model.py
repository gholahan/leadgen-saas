from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecipientStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    __table_args__ = (Index("idx_campaigns_user_id", "user_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    job_id: UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    subject: str = Field(sa_column=Column(Text, nullable=False))
    body: str = Field(sa_column=Column(Text, nullable=False))
    from_email: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: CampaignStatus = Field(
        default=CampaignStatus.DRAFT,
        sa_column=Column(SAEnum(CampaignStatus, name="campaign_status"), nullable=False),
    )
    celery_task_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    cancel_requested: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class CampaignRecipient(SQLModel, table=True):
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "enrichment_id", name="uq_campaign_recipient_enrichment"),
        Index("idx_campaign_recipients_campaign_id", "campaign_id"),
        Index("idx_campaign_recipients_lead_id", "lead_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", ondelete="CASCADE")
    lead_id: UUID = Field(foreign_key="leads.id", ondelete="CASCADE")
    enrichment_id: UUID = Field(foreign_key="lead_enrichments.id", ondelete="CASCADE")
    email: str = Field(sa_column=Column(Text, nullable=False))
    first_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: RecipientStatus = Field(
        default=RecipientStatus.PENDING,
        sa_column=Column(SAEnum(RecipientStatus, name="recipient_status"), nullable=False),
    )
    provider_message_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    sent_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
