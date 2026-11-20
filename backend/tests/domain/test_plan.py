import pytest

from app.domain.campaign_name import CampaignName
from app.domain.countries import CountryCode
from app.domain.errors import DomainError
from app.domain.offers import OfferSet
from app.domain.plan import GOOGLE_URL, GeoRedirectFlow, Placement, build_campaign_plan


def test_builds_geo_flow_then_offer_flow() -> None:
    placement = Placement(domain_id=5, group_id=7, traffic_source_id=9)
    plan = build_campaign_plan(
        name=CampaignName.from_suffix("c1"),
        countries=(CountryCode("AU"), CountryCode("RO")),
        offer_id=3749,
        placement=placement,
    )

    assert plan.name.value == "test_kondrashin_c1"
    assert plan.placement == placement
    assert plan.geo_flow.countries == (CountryCode("AU"), CountryCode("RO"))
    assert plan.offer_flow.offers == OfferSet.evenly([3749])


def test_geo_flow_requires_countries() -> None:
    with pytest.raises(DomainError):
        GeoRedirectFlow(countries=())


def test_geo_flow_rejects_duplicate_countries() -> None:
    with pytest.raises(DomainError):
        GeoRedirectFlow(countries=(CountryCode("AU"), CountryCode("AU")))


def test_geo_flow_redirects_to_google() -> None:
    assert GOOGLE_URL == "https://google.com"
