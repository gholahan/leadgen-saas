from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text, func
from sqlmodel import Field, SQLModel


class Export(SQLModel, table=True):
    __tablename__ = "exports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    type: str = Field(sa_column=Column(Text, nullable=False))
    storage_path: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )