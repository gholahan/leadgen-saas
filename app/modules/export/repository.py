import uuid
from sqlmodel import select

from app.modules.export.schema import ExportCreate
from app.database.session import SessionDep
from app.modules.export.model import Export
from app.modules.leads.model import Lead

async def create_export(user_id: uuid.UUID, export_data: ExportCreate, session: SessionDep):
    new_export = Export(
        id=uuid.uuid4(),
        job_id = export_data.job_id,
        user_id = user_id,
    )
    session.add(new_export)
    await session.commit()
    await session.refresh(new_export)
    return new_export


async def get_leads_for_export(
    job_id: uuid.UUID,
    session: SessionDep,
) -> list[Lead]:
    result = await session.exec(
        select(Lead).where(Lead.job_id == job_id)
    )
    return result.all()

async def get_export(export_id: uuid.UUID, session: SessionDep):
    result = await session.exec(
        select(Export).where(Export.id == export_id)
    )
    return result.one_or_none()


async def get_export_by_job(job_id: uuid.UUID, user_id: uuid.UUID, session: SessionDep):
    result = await session.exec(
        select(Export).where(Export.job_id == job_id, Export.user_id == user_id)
    )
    return result.one_or_none()

async def mark_export_completed(
    export_id: uuid.UUID,
    file_url: str,
    row_count: int,
    session: SessionDep,
):
    from datetime import datetime
    export = await get_export(export_id, session)

    if not export:
        raise ValueError(f"Export {export_id} not found")

    export.status = "COMPLETED"
    export.file_url = file_url
    export.row_count = row_count
    export.completed_at = datetime.utcnow()

    session.add(export)
    await session.commit()
    await session.refresh(export)

    return export