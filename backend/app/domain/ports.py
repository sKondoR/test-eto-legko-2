"""Порты: что домену и сервисам нужно от внешнего мира. Реализации — в app/adapters."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.campaign_name import CampaignName
from app.domain.offers import OfferChange, OfferSet, OfferShare
from app.domain.plan import CampaignPlan, GeoRedirectFlow, OfferFlow, Placement


@dataclass(frozen=True)
class CampaignSummary:
    id: int
    name: str


@dataclass(frozen=True)
class OfferSummary:
    id: int
    name: str


@dataclass(frozen=True)
class OfferHistoryEntry:
    changed_at: datetime
    change: OfferChange


@dataclass(frozen=True)
class CampaignState:
    """Кампания как есть в Keitaro. Ничего не проверяется: её могли править вручную."""

    id: int
    name: str
    geo_countries: tuple[str, ...]
    offer_flow_id: int | None
    offers: tuple[OfferShare, ...]
    # Офферы, выключенные в Keitaro: доля у них есть, а трафика нет.
    disabled_offer_ids: tuple[int, ...] = ()


class KeitaroPort(Protocol):
    async def resolve_placement(self) -> Placement:
        """ID домена, группы и источника. Имена берутся из настроек адаптера."""
        ...

    async def create_campaign(self, name: CampaignName, placement: Placement) -> int: ...

    async def create_geo_flow(self, campaign_id: int, flow: GeoRedirectFlow) -> None: ...

    async def create_offer_flow(self, campaign_id: int, flow: OfferFlow) -> None: ...

    async def archive_campaign(self, campaign_id: int) -> None: ...

    async def list_campaigns(self) -> list[CampaignSummary]: ...

    async def get_campaign(self, campaign_id: int) -> CampaignState: ...

    async def update_offer_flow(self, flow_id: int, offers: OfferSet) -> None: ...

    async def list_offers(self) -> list[OfferSummary]: ...


class CampaignLog(Protocol):
    async def campaign_created(self, keitaro_id: int, plan: CampaignPlan) -> None: ...

    async def campaign_failed(
        self, keitaro_id: int | None, plan: CampaignPlan, error: str
    ) -> None: ...

    async def offers_changed(self, keitaro_id: int, change: OfferChange) -> None: ...

    async def offer_history(self, keitaro_id: int) -> list[OfferHistoryEntry]:
        """Правки офферов кампании, новые первыми."""
        ...
