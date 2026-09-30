from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from app.modules.leads.model import Lead
from app.database.session import SessionDep
from app.modules.auth.dependencies import get_current_user
from app.modules.leads.schema import GetLeadsParams
from app.modules.leads.service import get_leads_service

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.get("/", response_model=list[Lead])
async def get_leads_endpoint(
    session: SessionDep,
    user=Depends(get_current_user),
    params: GetLeadsParams = Depends()
):
    leads = await get_leads_service(params, session)
    return leads