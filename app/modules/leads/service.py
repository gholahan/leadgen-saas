from uuid import UUID
from app.database.session import SessionDep

from app.modules.leads.repository import get_leads
from app.modules.leads.schema import GetLeadsParams


async def get_leads_service(params: GetLeadsParams, session: SessionDep):
    leads = await get_leads(session, params)
    return leads

# async def get_lead_by_job_id(job_id: UUID, session: SessionDep):
#     lead = await get_lead_by_job_id(job_id, session)
#     if not lead:
#         raise HTTPException(status_code=404, detail="Lead not found")
#     return lead