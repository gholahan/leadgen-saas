from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.jobs.router import router as jobs_router
from app.modules.leads.router import router as leads_router
from app.modules.export.router import router as export_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(jobs_router)
api_router.include_router(export_router)
api_router.include_router(leads_router)
