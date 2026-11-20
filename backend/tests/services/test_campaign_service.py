import pytest

from app.domain.errors import DomainError, KeitaroError
from app.domain.offers import OfferShare
from app.domain.plan import Placement
from app.domain.ports import CampaignState
from app.services.campaigns import CampaignService
from tests.services.fakes import FakeKeitaro, FakeLog

PLACEMENT = Placement(domain_id=5, group_id=7, traffic_source_id=9)


@pytest.fixture
def keitaro() -> FakeKeitaro:
    return FakeKeitaro(placement=PLACEMENT)


@pytest.fixture
def log() -> FakeLog:
    return FakeLog()


@pytest.fixture
def service(keitaro: FakeKeitaro, log: FakeLog) -> CampaignService:
    return CampaignService(keitaro, log)


async def test_creates_campaign_with_geo_and_offer_flows(
    service: CampaignService, keitaro: FakeKeitaro, log: FakeLog
) -> None:
    campaign_id = await service.create("c1", ["au", "RO"], offer_id=3749)

    campaign = keitaro.campaigns[campaign_id]
    assert campaign.name == "test_kondrashin_c1"
    assert campaign.geo_countries == ("AU", "RO")
    assert campaign.offers == (OfferShare(3749, 100),)
    assert keitaro.calls == [
        "resolve_placement",
        "create_campaign",
        "create_geo_flow",
        "create_offer_flow",
    ]
    [(logged_id, plan)] = log.created
    assert logged_id == campaign_id
    assert plan.placement == PLACEMENT


@pytest.mark.parametrize(
    ("suffix", "countries"),
    [("Bad Name", ["AU"]), ("c1", []), ("c1", ["XX"])],
)
async def test_invalid_input_never_reaches_keitaro(
    service: CampaignService, keitaro: FakeKeitaro, suffix: str, countries: list[str]
) -> None:
    with pytest.raises(DomainError):
        await service.create(suffix, countries, offer_id=1)
    assert keitaro.calls == []


async def test_unknown_placement_creates_nothing(
    service: CampaignService, keitaro: FakeKeitaro, log: FakeLog
) -> None:
    keitaro.placement = None
    with pytest.raises(KeitaroError):
        await service.create("c1", ["AU"], offer_id=1)
    assert keitaro.campaigns == {}
    assert log.created == log.failed == []


@pytest.mark.parametrize("failing", ["create_geo_flow", "create_offer_flow"])
async def test_flow_failure_archives_campaign_and_logs_failure(
    service: CampaignService, keitaro: FakeKeitaro, log: FakeLog, failing: str
) -> None:
    keitaro.fail_on.add(failing)

    with pytest.raises(KeitaroError, match=failing):
        await service.create("c1", ["AU"], offer_id=1)

    [campaign_id] = keitaro.campaigns
    assert keitaro.archived == [campaign_id]
    assert log.created == []
    [(logged_id, plan, error)] = log.failed
    assert logged_id == campaign_id
    assert plan.name.value == "test_kondrashin_c1"
    assert failing in error


async def test_geo_flow_failure_skips_offer_flow(
    service: CampaignService, keitaro: FakeKeitaro
) -> None:
    keitaro.fail_on.add("create_geo_flow")
    with pytest.raises(KeitaroError):
        await service.create("c1", ["AU"], offer_id=1)
    assert "create_offer_flow" not in keitaro.calls


async def test_campaign_creation_failure_logs_without_id(
    service: CampaignService, keitaro: FakeKeitaro, log: FakeLog
) -> None:
    keitaro.fail_on.add("create_campaign")
    with pytest.raises(KeitaroError):
        await service.create("c1", ["AU"], offer_id=1)
    assert keitaro.archived == []
    [(logged_id, _, _)] = log.failed
    assert logged_id is None


async def test_archive_failure_keeps_original_error_and_logs_both(
    service: CampaignService, keitaro: FakeKeitaro, log: FakeLog
) -> None:
    keitaro.fail_on.update({"create_offer_flow", "archive_campaign"})

    with pytest.raises(KeitaroError, match="create_offer_flow"):
        await service.create("c1", ["AU"], offer_id=1)

    [(_, _, error)] = log.failed
    assert "create_offer_flow" in error
    assert "archive_campaign" in error


async def test_lists_only_our_campaigns(service: CampaignService, keitaro: FakeKeitaro) -> None:
    ours = await service.create("c1", ["AU"], offer_id=1)
    keitaro.campaigns[1] = CampaignState(1, "test_ivanov_c1", (), None, ())

    assert [c.id for c in await service.list_ours()] == [ours]
