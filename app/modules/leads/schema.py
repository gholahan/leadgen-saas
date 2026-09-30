from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class GetLeadsParams(BaseModel):
    job_id: Optional[UUID] = None
    has_email: Optional[bool] = None
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None
    min_review_count: Optional[int] = None
    max_review_count: Optional[int] = None
