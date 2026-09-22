from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.jobs.router import router as jobs_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(jobs_router)
