from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.errors import ConflictError, DomainError
from app.domain.offers import OfferSet, OfferShare, diff, is_even_split
from app.domain.ports import CampaignLog, CampaignState, KeitaroPort


@dataclass(frozen=True)
class EditorView:
    campaign: CampaignState
    is_even: bool  # False — сохранение перезапишет ручные доли, интерфейс предупреждает


class OfferEditor:
    def __init__(self, keitaro: KeitaroPort, log: CampaignLog) -> None:
        self._keitaro = keitaro
        self._log = log

    async def open(self, campaign_id: int) -> EditorView:
        campaign = await self._keitaro.get_campaign(campaign_id)
        return EditorView(campaign, is_even_split(campaign.offers))

    async def save(
        self, campaign_id: int, expected: Sequence[OfferShare], offer_ids: Sequence[int]
    ) -> OfferSet:
        """Сохраняет итоговый список офферов с равными долями.

        expected — офферы, которые редактор показал пользователю. Если в Keitaro они уже
        другие, сохранение затёрло бы чужую правку, поэтому бросается ConflictError.
        """
        offers = OfferSet.evenly(offer_ids)
        campaign = await self._keitaro.get_campaign(campaign_id)
        if campaign.offer_flow_id is None:
            raise DomainError("В кампании нет потока с офферами")
        if campaign.offers != tuple(expected):
            raise ConflictError("Поток изменили в Keitaro. Обновите страницу и повторите правку")

        change = diff(campaign.offers, offers)
        if not change.is_empty:
            await self._keitaro.update_offer_flow(campaign.offer_flow_id, offers)
            await self._log.offers_changed(campaign_id, change)
        return offers
