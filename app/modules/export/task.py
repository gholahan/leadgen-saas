import asyncio
from uuid import UUID
from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.celery import celery_app
from app.database.session import engine
from app.modules.export.csv import generate_csv
from app.modules.export.repository import (
    get_export,
    get_leads_for_export,
    mark_export_completed,
)
from app.modules.export.storage import upload_csv


@celery_app.task(name="exports.generate_csv")
def generate_csv_export(export_id: str):
    asyncio.run(_run_export(UUID(export_id)))


async def _run_export(export_id: UUID):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        export = await get_export(export_id, session)

        if not export:
            raise ValueError(f"Export {export_id} not found")

        leads = await get_leads_for_export(
            job_id=export.job_id,
            session=session,
        )

        csv_content = generate_csv(leads)

        file_path = f"{export.user_id}/{export.job_id}/{export.id}.csv"

        file_url = upload_csv(
            file=csv_content,
            file_path=file_path,
        )

        await mark_export_completed(
            export_id=export.id,
            file_url=file_url,
            row_count=len(leads),
            session=session,
        )