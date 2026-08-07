from sqlmodel import SQLModel

# Import all models so Alembic can detect them
# from app.modules.auth.model import User  # noqa
# from app.modules.jobs.model import Job   # noqa

__all__ = ["SQLModel"]
