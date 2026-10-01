from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from enum import Enum
from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlmodel import Field, SQLModel


class ExportStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Export(SQLModel, table=True):
    __tablename__ = "exports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    status: str = Field(default=ExportStatus.PENDING, sa_column=Column(Text, nullable=False))
    file_url: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    row_count: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )