from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL not available")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={
        "statement_cache_size": 0
    },
    execution_options={
        "compiled_cache": None
    }
)


def make_celery_engine() -> AsyncEngine:
    """Create a NullPool engine for use inside Celery tasks.

    Celery tasks run inside asyncio.run() which creates a fresh event loop.
    Reusing the module-level pooled engine across event loops causes stale
    connection errors (ConnectionDoesNotExistError) on Neon and similar
    serverless Postgres providers. NullPool opens a fresh connection per
    session and closes it immediately — safe for short-lived task contexts.
    """
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
        execution_options={"compiled_cache": None},
    )


async def get_session():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]