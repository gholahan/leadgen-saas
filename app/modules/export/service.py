from fastapi import HTTPException
from uuid import UUID
from app.modules.export.repository import create_export, ExportCreate, get_export_by_job
from app.modules.jobs.service import get_job_by_id
from app.database.session import SessionDep
from app.modules.export.task import generate_csv_export
from app.modules.export.model import ExportStatus


async def verify_user_job(job_id: UUID, user_id: UUID, session: SessionDep):
    job = await get_job_by_id(job_id, session)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this job")
    return job


async def create_export_service(user_id: UUID, job_id: UUID, export_data: ExportCreate, session: SessionDep):
    await verify_user_job(job_id=job_id, user_id=user_id, session=session)
    export = await create_export(user_id=user_id, export_data=export_data, session=session)
    if not export:
        raise HTTPException(status_code=500, detail="Failed to create export")
    generate_csv_export.delay(str(export.id))
    return export


async def download_export_service(job_id: UUID, user_id: UUID, session: SessionDep):
    export = await get_export_by_job(job_id=job_id, user_id=user_id, session=session)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.status != ExportStatus.COMPLETED:
        raise HTTPException(status_code=409, detail=f"Export is not ready, current status: {export.status}")
    if not export.file_url:
        raise HTTPException(status_code=500, detail="Export file missing")
    return {"download_url": export.file_url}
