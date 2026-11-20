from dataclasses import dataclass

from app.domain.campaign_name import CampaignName
from app.domain.countries import NO_COUNTRIES, CountryCode
from app.domain.errors import DomainError
from app.domain.offers import OfferSet

GOOGLE_URL = "https://google.com"


@dataclass(frozen=True)
class Placement:
    """Куда кладётся кампания в Keitaro: домен, группа и источник трафика."""

    domain_id: int
    group_id: int
    traffic_source_id: int


@dataclass(frozen=True)
class GeoRedirectFlow:
    """Поток 1: трафик из выбранных стран уходит на redirect_url."""

    countries: tuple[CountryCode, ...]
    redirect_url: str = GOOGLE_URL

    def __post_init__(self) -> None:
        if not self.countries:
            raise DomainError(NO_COUNTRIES)
        if len(set(self.countries)) != len(self.countries):
            raise DomainError("Страны в фильтре повторяются")


@dataclass(frozen=True)
class OfferFlow:
    """Поток 2: весь остальной трафик делится между офферами."""

    offers: OfferSet


@dataclass(frozen=True)
class CampaignPlan:
    name: CampaignName
    placement: Placement
    geo_flow: GeoRedirectFlow
    offer_flow: OfferFlow


def build_campaign_plan(
    name: CampaignName,
    countries: tuple[CountryCode, ...],
    offer_id: int,
    placement: Placement,
) -> CampaignPlan:
    return CampaignPlan(
        name=name,
        placement=placement,
        geo_flow=GeoRedirectFlow(countries=countries),
        offer_flow=OfferFlow(offers=OfferSet.evenly([offer_id])),
    )
