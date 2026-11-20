from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.campaign_name import PREFIX, is_ours
from app.domain.errors import ConflictError, DomainError
from app.domain.offers import OfferSet, OfferShare, diff, is_even_split
from app.domain.ports import CampaignLog, CampaignState, KeitaroPort


@dataclass(frozen=True)
class EditorView:
    campaign: CampaignState
    # False — доли ручные или часть офферов выключена в Keitaro: интерфейс предупреждает.
    is_even: bool


class OfferEditor:
    def __init__(self, keitaro: KeitaroPort, log: CampaignLog) -> None:
        self._keitaro = keitaro
        self._log = log

    async def open(self, campaign_id: int) -> EditorView:
        campaign = await self._get_ours(campaign_id)
        is_even = is_even_split(campaign.offers) and not campaign.disabled_offer_ids
        return EditorView(campaign, is_even)

    async def save(
        self, campaign_id: int, expected: Sequence[OfferShare], offer_ids: Sequence[int]
    ) -> OfferSet:
        """Сохраняет итоговый список офферов с равными долями.

        expected — офферы, которые редактор показал пользователю. Если в Keitaro они уже
        другие, сохранение затёрло бы чужую правку, поэтому бросается ConflictError.
        """
        offers = OfferSet.evenly(offer_ids)
        campaign = await self._get_ours(campaign_id)
        if campaign.offer_flow_id is None:
            raise DomainError("В кампании нет потока с офферами")
        if campaign.offers != tuple(expected):
            raise ConflictError("Поток изменили в Keitaro. Обновите страницу и повторите правку")

        change = diff(campaign.offers, offers)
        if not change.is_empty:
            await self._keitaro.update_offer_flow(campaign.offer_flow_id, offers)
            await self._log.offers_changed(campaign_id, change)
        return offers

    async def _get_ours(self, campaign_id: int) -> CampaignState:
        campaign = await self._keitaro.get_campaign(campaign_id)
        if not is_ours(campaign.name):
            raise DomainError(f"Редактировать можно только кампании с префиксом {PREFIX}")
        return campaign
