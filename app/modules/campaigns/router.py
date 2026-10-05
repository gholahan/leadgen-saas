from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.database.session import SessionDep
from app.modules.auth.dependencies import get_current_user
from app.modules.campaigns.repository import get_campaign, get_recipients, get_user_campaigns
from app.modules.campaigns.schema import CampaignCreate, CampaignResponse, RecipientResponse
from app.modules.campaigns.service import cancel_campaign, create_new_campaign, start_campaign

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign_endpoint(
    payload: CampaignCreate,
    session: SessionDep,
    user=Depends(get_current_user),
):
    try:
        campaign = await create_new_campaign(
            user_id=user.id,
            job_id=payload.job_id,
            subject=payload.subject,
            body=payload.body,
            from_email=payload.from_email,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return campaign


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(session: SessionDep, user=Depends(get_current_user)):
    return await get_user_campaigns(user.id, session)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_endpoint(
    campaign_id: UUID,
    session: SessionDep,
    user=Depends(get_current_user),
):
    campaign = await get_campaign(campaign_id, session)
    if not campaign or campaign.user_id != user.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign_endpoint(
    campaign_id: UUID,
    session: SessionDep,
    user=Depends(get_current_user),
):
    try:
        return await start_campaign(campaign_id, user.id, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{campaign_id}/cancel", response_model=CampaignResponse)
async def cancel_campaign_endpoint(
    campaign_id: UUID,
    session: SessionDep,
    user=Depends(get_current_user),
):
    try:
        return await cancel_campaign(campaign_id, user.id, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{campaign_id}/recipients", response_model=list[RecipientResponse])
async def get_campaign_recipients(
    campaign_id: UUID,
    session: SessionDep,
    user=Depends(get_current_user),
):
    campaign = await get_campaign(campaign_id, session)
    if not campaign or campaign.user_id != user.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await get_recipients(campaign_id, session)
