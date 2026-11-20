from collections.abc import Sequence

from app.domain.campaign_name import CampaignName, is_ours
from app.domain.countries import parse_countries
from app.domain.errors import KeitaroError
from app.domain.plan import build_campaign_plan
from app.domain.ports import (
    CampaignLog,
    CampaignSummary,
    DomainSummary,
    KeitaroPort,
    OfferSummary,
)


class CampaignService:
    def __init__(self, keitaro: KeitaroPort, log: CampaignLog) -> None:
        self._keitaro = keitaro
        self._log = log

    async def create(
        self, name_suffix: str, countries: Sequence[str], offer_id: int, domain_id: int
    ) -> int:
        """Создаёт кампанию с двумя потоками. Если поток не создался — кампания уходит в архив."""
        name = CampaignName.from_suffix(name_suffix)
        geo = parse_countries(countries)
        placement = await self._keitaro.resolve_placement(domain_id)
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
        return [c for c in await self._keitaro.list_campaigns() if is_ours(c.name)]

    async def list_offers(self) -> list[OfferSummary]:
        return await self._keitaro.list_offers()

    async def list_domains(self) -> list[DomainSummary]:
        return await self._keitaro.list_domains()
