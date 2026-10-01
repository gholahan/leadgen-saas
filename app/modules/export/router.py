from uuid import UUID
from app.database.session import SessionDep
from app.modules.export.service import create_export_service, download_export_service
from app.modules.export.schema import ExportResponse, ExportCreate, DownloadResponse
from app.modules.auth.dependencies import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/jobs", tags=["export"])


@router.post("/{job_id}/export", status_code=201)
async def export_job(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    return await create_export_service(user_id=user.id, job_id=job_id, export_data=ExportCreate(job_id=job_id), session=session)


@router.get("/{job_id}/export/download", response_model=DownloadResponse)
async def download_export(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    return await download_export_service(job_id=job_id, user_id=user.id, session=session)