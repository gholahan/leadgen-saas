from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class EmailStatus(str, Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    REPLIED = "REPLIED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"


class Email(SQLModel, table=True):
    __tablename__ = "emails"
    __table_args__ = (
        Index("idx_emails_campaign_id", "campaign_id"),
        Index("idx_emails_lead_id", "lead_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", ondelete="CASCADE")
    lead_id: UUID = Field(foreign_key="leads.id", ondelete="CASCADE")
    provider: str = Field(sa_column=Column(Text, nullable=False))
    status: EmailStatus = Field(
        default=EmailStatus.QUEUED,
        sa_column=Column(SAEnum(EmailStatus, name="email_status"), nullable=False),
    )
    subject: str = Field(sa_column=Column(Text, nullable=False))
    sent_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))