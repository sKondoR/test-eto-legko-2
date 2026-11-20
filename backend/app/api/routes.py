from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas import (
    CampaignCreatedOut,
    CampaignCreateIn,
    ConfigOut,
    EditorOut,
    ErrorOut,
    HistoryEntryOut,
    OffersSavedOut,
    OffersSaveIn,
)
from app.domain.campaign_name import PREFIX
from app.domain.countries import ISO_CODES
from app.domain.ports import CampaignSummary, OfferSummary
from app.services.campaigns import CampaignService
from app.services.offer_editor import OfferEditor

# Ошибки сервисов приходят как {"detail": "<текст для пользователя>"}; коды — в app.main.
router = APIRouter(
    prefix="/api",
    responses={code: {"model": ErrorOut} for code in (404, 409, 502)},
)


def _campaigns(request: Request) -> CampaignService:
    return request.app.state.campaigns


def _editor(request: Request) -> OfferEditor:
    return request.app.state.editor


Campaigns = Annotated[CampaignService, Depends(_campaigns)]
Editor = Annotated[OfferEditor, Depends(_editor)]


@router.get("/config")
def get_config(request: Request) -> ConfigOut:
    return ConfigOut(
        name_prefix=PREFIX,
        default_geo=[c.value for c in request.app.state.default_geo],
        countries=sorted(ISO_CODES),
    )


@router.get("/offers")
async def list_offers(campaigns: Campaigns) -> list[OfferSummary]:
    return await campaigns.list_offers()


@router.get("/campaigns")
async def list_campaigns(campaigns: Campaigns) -> list[CampaignSummary]:
    return await campaigns.list_ours()


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignCreateIn, campaigns: Campaigns) -> CampaignCreatedOut:
    campaign_id = await campaigns.create(body.name_suffix, body.countries, body.offer_id)
    return CampaignCreatedOut(id=campaign_id)


@router.get("/campaigns/{campaign_id}")
async def open_editor(campaign_id: int, editor: Editor) -> EditorOut:
    view = await editor.open(campaign_id)
    campaign = view.campaign
    return EditorOut(
        id=campaign.id,
        name=campaign.name,
        geo=campaign.geo_countries,
        offers=campaign.offers,
        disabled_offer_ids=campaign.disabled_offer_ids,
        is_even=view.is_even,
        history=[
            HistoryEntryOut(
                changed_at=entry.changed_at,
                before=entry.change.before,
                after=entry.change.after,
                added=entry.change.added,
                removed=entry.change.removed,
            )
            for entry in view.history
        ],
    )


@router.put("/campaigns/{campaign_id}/offers")
async def save_offers(campaign_id: int, body: OffersSaveIn, editor: Editor) -> OffersSavedOut:
    saved = await editor.save(campaign_id, body.expected, body.offer_ids)
    return OffersSavedOut(offers=saved.shares)
