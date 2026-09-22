from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.jobs.model import JobStatus, StepStatus


# ── Requests ──────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    industry: str
    location: str
    target_count: int


# ── Responses ─────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    id: UUID
    user_id: UUID
    industry: str
    location: str
    target_count: int
    status: JobStatus
    progress: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    celery_task_id: str | None = None
    cancel_requested: bool = False

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    id: UUID
    status: JobStatus
    progress: int

    model_config = {"from_attributes": True}


class JobProgressResponse(BaseModel):
    progress: int

    model_config = {"from_attributes": True}


class JobMessageResponse(BaseModel):
    message: str


# ── Step Responses ────────────────────────────────────────────────────

class JobStepResponse(BaseModel):
    id: UUID
    job_id: UUID
    step_name: str
    status: StepStatus
    started_at: datetime | None
    completed_at: datetime | None
    input_data: dict | None
    output_data: dict | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobStepsResponse(BaseModel):
    steps: list[JobStepResponse]

    model_config = {"from_attributes": True}


# ── Log Responses ─────────────────────────────────────────────────────

class JobLogEntry(BaseModel):
    step_name: str
    status: StepStatus
    message: str
    timestamp: datetime
    error: str | None = None


class JobLogsResponse(BaseModel):
    logs: list[JobLogEntry]

    model_config = {"from_attributes": True}
