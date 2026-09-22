from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import DateTime, Index, Text, UniqueConstraint, func, Column
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import INET



class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="users_email_key"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: str = Field(sa_column=Column(Text, nullable=False))
    email: str = Field(sa_column=Column(Text, nullable=False))
    password_hash: str = Field(sa_column=Column(Text, nullable=False))

    plan: str = Field(default="free", sa_column=Column(Text, nullable=False, server_default="free"))
    credits: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    )


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
        Index("idx_refresh_tokens_expires", "expires_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")

    token_hash: str = Field(sa_column=Column(Text, nullable=False, unique=True))

    device_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    ip_address: str | None = Field(
        default=None,
        sa_column=Column(INET, nullable=True),
    )

    user_agent: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )