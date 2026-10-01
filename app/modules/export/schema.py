from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ExportCreate(BaseModel):
    job_id: UUID


class ExportResponse(BaseModel):
    id: UUID
    job_id: UUID
    user_id: UUID
    storage_url: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExportStatusResponse(BaseModel):
    id: UUID
    job_id: UUID
    user_id: UUID
    type: str
    storage_path: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ExportMessageResponse(BaseModel):
    message: str


class DownloadResponse(BaseModel):
    download_url: str