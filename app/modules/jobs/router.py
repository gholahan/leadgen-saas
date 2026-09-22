from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from app.modules.jobs.schema import JobCreate, JobResponse, JobStatusResponse, JobProgressResponse, JobMessageResponse
from app.modules.auth.dependencies import get_current_user
from app.database.session import SessionDep
from app.modules.jobs.model import JobStatus
from app.modules.jobs.service import (
    create_new_job,
    get_user_jobs,
    get_job_by_id,
    delete_job,
    cancel_job_service,
    JobAlreadyFinished,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job_endpoint(payload: JobCreate, session: SessionDep, user=Depends(get_current_user)):
    return await create_new_job(user.id, payload, session)


@router.get("/", response_model=list[JobResponse])
async def get_user_jobs_endpoint(session: SessionDep, user=Depends(get_current_user)):
    return await get_user_jobs(session, user)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id_endpoint(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    job = await get_job_by_id(job_id, session)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress_endpoint(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    job = await get_job_by_id(job_id, session)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"progress": job.progress}


@router.post("/{job_id}/cancel", response_model=JobMessageResponse)
async def cancel_job_endpoint(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    job = await get_job_by_id(job_id, session)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed, failed, or already cancelled job")
    try:
        await cancel_job_service(job_id=job_id, user_id=user.id, session=session)
    except JobAlreadyFinished:
        raise HTTPException(status_code=400, detail="Job has already finished and cannot be cancelled")
    return JobMessageResponse(message=f"Job {job_id} cancellation requested.")


@router.delete("/{job_id}", response_model=JobMessageResponse)
async def delete_job_endpoint(job_id: UUID, session: SessionDep, user=Depends(get_current_user)):
    job = await get_job_by_id(job_id, session)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await delete_job(job_id=job.id, session=session)
    return JobMessageResponse(message=f"Job {job_id} has been deleted.")
