import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SAEnum, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="jobs_progress_check",
        ),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_user_id", "user_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
    )

    industry: str = Field(sa_column=Column(Text, nullable=False))
    location: str = Field(sa_column=Column(Text, nullable=False))
    target_count: int

    status: JobStatus = Field(
        default=JobStatus.PENDING,
        sa_column=Column(
            SAEnum(
                JobStatus,
                name="job_status",
                native_enum=True,
            ),
            nullable=False,
            default=JobStatus.PENDING,
        ),
    )

    progress: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    celery_task_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    cancel_requested: bool = Field(default=False)


class JobStep(SQLModel, table=True):
    __tablename__ = "job_steps"
    __table_args__ = (Index("idx_job_steps_job_id", "job_id"),)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )

    job_id: uuid.UUID = Field(
        foreign_key="jobs.id",
        ondelete="CASCADE",
    )

    step_name: str = Field(sa_column=Column(Text, nullable=False))

    status: StepStatus = Field(
        default=StepStatus.PENDING  ,
        sa_column=Column(
            SAEnum(
                StepStatus,
                name="step_status",
                native_enum=True,
            ),
            nullable=False,
            default=StepStatus.PENDING,
        ),
    )

    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    input_json: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))

    output_json: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))

    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    celery_task_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    cancel_requested: bool = Field(default=False)
