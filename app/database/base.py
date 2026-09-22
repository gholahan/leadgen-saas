from sqlmodel import SQLModel

# Import all models so Alembic can detect them
from app.modules.auth.model import RefreshToken, User  # noqa
from app.modules.campaigns.model import Campaign, CampaignLead  # noqa
from app.modules.email.model import Email  # noqa
from app.modules.export.model import Export  # noqa
from app.modules.jobs.model import Job, JobStep  # noqa
from app.modules.leads.model import Lead  # noqa

__all__ = ["SQLModel"]
