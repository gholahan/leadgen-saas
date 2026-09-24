from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, Index, Integer, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class Lead(SQLModel, table=True):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("lead_score >= 0 AND lead_score <= 100", name="leads_lead_score_check"),
        CheckConstraint("verification_score >= 0 AND verification_score <= 100", name="leads_verification_score_check"),
        Index("idx_leads_job_id", "job_id"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_place_id", "place_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    company_name: str = Field(sa_column=Column(Text, nullable=False))
    website: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    email: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    phone: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    address: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    city: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    state: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    country: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    industry: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    google_maps_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    place_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    rating: Decimal | None = Field(default=None, sa_column=Column(Numeric(2, 1), nullable=True))
    review_count: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    lead_score: int | None = Field(default=0, sa_column=Column(Integer, nullable=True, server_default="0"))
    verification_status: VerificationStatus | None = Field(
        default=VerificationStatus.PENDING,
        sa_column=Column(SAEnum(VerificationStatus, name="verification_status"), nullable=True),
    )
    verification_score: int | None = Field(default=0, sa_column=Column(Integer, nullable=True, server_default="0"))
    status: str | None = Field(default="NEW", sa_column=Column(Text, nullable=True, server_default="NEW"))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )