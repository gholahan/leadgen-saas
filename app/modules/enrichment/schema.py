from pydantic import BaseModel


class EnrichmentResult(BaseModel):
    email: str | None = None
    email_type: str | None = None
    email_score: int | None = None
    domain: str | None = None
    first_name: str | None = None
    status: str = "NOT_FOUND"
