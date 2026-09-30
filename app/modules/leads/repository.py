from app.modules.leads.model import Lead
from sqlmodel import select
from app.database.session import SessionDep
from app.modules.leads.schema import GetLeadsParams


async def get_leads(session: SessionDep, param: GetLeadsParams):
    query = select(Lead)
    if param.job_id:
        query = query.where(Lead.job_id == param.job_id)
    if param.has_email is not None:
        if param.has_email:
            query = query.where(Lead.email.isnot(None))
        else:
            query = query.where(Lead.email.is_(None))
    if param.min_rating is not None:
        query = query.where(Lead.rating >= param.min_rating)
    if param.max_rating is not None:
        query = query.where(Lead.rating <= param.max_rating)
    if param.min_review_count is not None:
        query = query.where(Lead.review_count >= param.min_review_count)
    if param.max_review_count is not None:
        query = query.where(Lead.review_count <= param.max_review_count)
    result = await session.exec(query)
    leads = result.all()
    return leads


# async def get_lead_by_job_id(job_id: UUID, session: SessionDep):
#     results=await session.exec(select(Lead).where(Lead.Job_id == job_id))
#     leads = results.all()
#     return leads