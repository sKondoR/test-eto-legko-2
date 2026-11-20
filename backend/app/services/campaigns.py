from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.campaign_name import PREFIX, CampaignName
from app.domain.countries import parse_countries
from app.domain.errors import KeitaroError
from app.domain.plan import build_campaign_plan
from app.domain.ports import CampaignLog, CampaignSummary, KeitaroPort


@dataclass(frozen=True)
class PlacementNames:
    """Домен, группа и источник новых кампаний — по именам, как в админке Keitaro."""

    domain: str
    group: str
    source: str


class CampaignService:
    def __init__(self, keitaro: KeitaroPort, log: CampaignLog, placement: PlacementNames) -> None:
        self._keitaro = keitaro
        self._log = log
        self._placement = placement

    async def create(self, name_suffix: str, countries: Sequence[str], offer_id: int) -> int:
        """Создаёт кампанию с двумя потоками. Если поток не создался — кампания уходит в архив."""
        name = CampaignName.from_suffix(name_suffix)
        geo = parse_countries(countries)
        p = self._placement
        placement = await self._keitaro.resolve_placement(p.domain, p.group, p.source)
        plan = build_campaign_plan(name, geo, offer_id, placement)

        campaign_id: int | None = None
        try:
            campaign_id = await self._keitaro.create_campaign(plan.name, plan.placement)
            await self._keitaro.create_geo_flow(campaign_id, plan.geo_flow)
            await self._keitaro.create_offer_flow(campaign_id, plan.offer_flow)
        except KeitaroError as error:
            reason = str(error)
            if campaign_id is not None:
                try:
                    await self._keitaro.archive_campaign(campaign_id)
                except KeitaroError as archive_error:
                    reason += f"; архивировать кампанию {campaign_id} не удалось: {archive_error}"
            await self._log.campaign_failed(campaign_id, plan, reason)
            raise

        await self._log.campaign_created(campaign_id, plan)
        return campaign_id

    async def list_ours(self) -> list[CampaignSummary]:
        return [c for c in await self._keitaro.list_campaigns() if c.name.startswith(PREFIX)]
