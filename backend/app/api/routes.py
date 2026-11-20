from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas import (
    CampaignCreatedOut,
    CampaignCreateIn,
    CampaignOut,
    ConfigOut,
    EditorOut,
    ErrorOut,
    HistoryEntryOut,
    OfferOut,
    OfferShareModel,
    OffersSavedOut,
    OffersSaveIn,
)
from app.domain.campaign_name import PREFIX
from app.domain.countries import ISO_CODES
from app.domain.offers import OfferShare
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
async def list_offers(campaigns: Campaigns) -> list[OfferOut]:
    return [OfferOut(id=o.id, name=o.name) for o in await campaigns.list_offers()]


@router.get("/campaigns")
async def list_campaigns(campaigns: Campaigns) -> list[CampaignOut]:
    return [CampaignOut(id=c.id, name=c.name) for c in await campaigns.list_ours()]


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
        geo=list(campaign.geo_countries),
        offers=_shares_out(campaign.offers),
        disabled_offer_ids=list(campaign.disabled_offer_ids),
        is_even=view.is_even,
        history=[
            HistoryEntryOut(
                changed_at=entry.changed_at,
                before=_shares_out(entry.change.before),
                after=_shares_out(entry.change.after),
                added=list(entry.change.added),
                removed=list(entry.change.removed),
            )
            for entry in view.history
        ],
    )


@router.put("/campaigns/{campaign_id}/offers")
async def save_offers(campaign_id: int, body: OffersSaveIn, editor: Editor) -> OffersSavedOut:
    expected = [OfferShare(s.offer_id, s.share) for s in body.expected]
    saved = await editor.save(campaign_id, expected, body.offer_ids)
    return OffersSavedOut(offers=_shares_out(saved.shares))


def _shares_out(shares: Sequence[OfferShare]) -> list[OfferShareModel]:
    return [OfferShareModel(offer_id=s.offer_id, share=s.share) for s in shares]
