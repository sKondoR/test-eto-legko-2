"""In-memory реализации портов для тестов сервисов."""

from dataclasses import dataclass, field, replace

from app.domain.campaign_name import CampaignName
from app.domain.errors import KeitaroError
from app.domain.offers import OfferChange, OfferSet
from app.domain.plan import CampaignPlan, GeoRedirectFlow, OfferFlow, Placement
from app.domain.ports import CampaignState, CampaignSummary


@dataclass
class FakeKeitaro:
    placement: Placement | None = None  # None — размещение в Keitaro не найдено
    campaigns: dict[int, CampaignState] = field(default_factory=dict)
    archived: list[int] = field(default_factory=list)
    fail_on: set[str] = field(default_factory=set)  # имена методов, которые бросят KeitaroError
    calls: list[str] = field(default_factory=list)
    _next_id: int = field(default=100, init=False, repr=False)

    def _call(self, method: str) -> None:
        self.calls.append(method)
        if method in self.fail_on:
            raise KeitaroError(f"{method} упал")

    async def resolve_placement(self) -> Placement:
        self._call("resolve_placement")
        if self.placement is None:
            raise KeitaroError("Размещение не найдено")
        return self.placement

    async def create_campaign(self, name: CampaignName, placement: Placement) -> int:
        self._call("create_campaign")
        self._next_id += 1
        self.campaigns[self._next_id] = CampaignState(self._next_id, name.value, (), None, ())
        return self._next_id

    async def create_geo_flow(self, campaign_id: int, flow: GeoRedirectFlow) -> None:
        self._call("create_geo_flow")
        codes = tuple(c.value for c in flow.countries)
        self.campaigns[campaign_id] = replace(self.campaigns[campaign_id], geo_countries=codes)

    async def create_offer_flow(self, campaign_id: int, flow: OfferFlow) -> None:
        self._call("create_offer_flow")
        self.campaigns[campaign_id] = replace(
            self.campaigns[campaign_id], offer_flow_id=campaign_id * 10, offers=flow.offers.shares
        )

    async def archive_campaign(self, campaign_id: int) -> None:
        self._call("archive_campaign")
        self.archived.append(campaign_id)

    async def list_campaigns(self) -> list[CampaignSummary]:
        self._call("list_campaigns")
        return [CampaignSummary(c.id, c.name) for c in self.campaigns.values()]

    async def get_campaign(self, campaign_id: int) -> CampaignState:
        self._call("get_campaign")
        return self.campaigns[campaign_id]

    async def update_offer_flow(self, flow_id: int, offers: OfferSet) -> None:
        self._call("update_offer_flow")
        for c in self.campaigns.values():
            if c.offer_flow_id == flow_id:
                self.campaigns[c.id] = replace(c, offers=offers.shares)


@dataclass
class FakeLog:
    created: list[tuple[int, CampaignPlan]] = field(default_factory=list)
    failed: list[tuple[int | None, CampaignPlan, str]] = field(default_factory=list)
    changes: list[tuple[int, OfferChange]] = field(default_factory=list)

    async def campaign_created(self, keitaro_id: int, plan: CampaignPlan) -> None:
        self.created.append((keitaro_id, plan))

    async def campaign_failed(self, keitaro_id: int | None, plan: CampaignPlan, error: str) -> None:
        self.failed.append((keitaro_id, plan, error))

    async def offers_changed(self, keitaro_id: int, change: OfferChange) -> None:
        self.changes.append((keitaro_id, change))
