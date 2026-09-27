from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Integer, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class EnrichmentStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"


class LeadEnrichment(SQLModel, table=True):
    __tablename__ = "lead_enrichments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lead_id: UUID = Field(foreign_key="leads.id", ondelete="CASCADE")
    provider: str = Field(sa_column=Column(Text, nullable=False))
    email: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    email_type: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    email_score: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    domain: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: EnrichmentStatus = Field(
        default=EnrichmentStatus.NOT_FOUND,
        sa_column=Column(SAEnum(EnrichmentStatus, name="enrichment_status"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
