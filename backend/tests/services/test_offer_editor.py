import pytest

from app.domain.errors import ConflictError, DomainError
from app.domain.offers import OfferShare
from app.domain.ports import CampaignState
from app.services.offer_editor import OfferEditor
from tests.helpers import shares
from tests.services.fakes import FakeKeitaro, FakeLog

CAMPAIGN_ID = 1
FLOW_ID = 10


def keitaro_with(offers: tuple[OfferShare, ...], flow_id: int | None = FLOW_ID) -> FakeKeitaro:
    state = CampaignState(CAMPAIGN_ID, "test_kondrashin_c1", ("AU",), flow_id, offers)
    return FakeKeitaro(campaigns={CAMPAIGN_ID: state})


async def test_open_shows_campaign_as_is_and_flags_manual_shares() -> None:
    keitaro = keitaro_with(shares((1, 70), (2, 30)))

    view = await OfferEditor(keitaro, FakeLog()).open(CAMPAIGN_ID)

    assert view.campaign.offers == shares((1, 70), (2, 30))
    assert view.campaign.geo_countries == ("AU",)
    assert not view.is_even


async def test_save_splits_evenly_and_logs_change() -> None:
    keitaro, log = keitaro_with(shares((1, 50), (2, 50))), FakeLog()

    saved = await OfferEditor(keitaro, log).save(
        CAMPAIGN_ID, expected=shares((1, 50), (2, 50)), offer_ids=[2, 3, 4]
    )

    assert saved.shares == shares((2, 33), (3, 33), (4, 34))
    assert keitaro.campaigns[CAMPAIGN_ID].offers == saved.shares
    [(campaign_id, change)] = log.changes
    assert campaign_id == CAMPAIGN_ID
    assert change.added == (3, 4)
    assert change.removed == (1,)


async def test_save_rejects_when_keitaro_changed_meanwhile() -> None:
    keitaro, log = keitaro_with(shares((1, 50), (2, 50))), FakeLog()

    with pytest.raises(ConflictError):
        await OfferEditor(keitaro, log).save(
            CAMPAIGN_ID, expected=shares((1, 100)), offer_ids=[1, 3]
        )

    assert "update_offer_flow" not in keitaro.calls
    assert log.changes == []


async def test_save_without_changes_does_nothing() -> None:
    keitaro, log = keitaro_with(shares((1, 50), (2, 50))), FakeLog()

    await OfferEditor(keitaro, log).save(
        CAMPAIGN_ID, expected=shares((1, 50), (2, 50)), offer_ids=[1, 2]
    )

    assert "update_offer_flow" not in keitaro.calls
    assert log.changes == []


async def test_save_repairs_hand_broken_flow() -> None:
    broken = shares((1, 50), (1, 50))
    keitaro, log = keitaro_with(broken), FakeLog()

    await OfferEditor(keitaro, log).save(CAMPAIGN_ID, expected=broken, offer_ids=[1])

    assert keitaro.campaigns[CAMPAIGN_ID].offers == shares((1, 100))


async def test_save_rejects_empty_offer_list() -> None:
    keitaro = keitaro_with(shares((1, 100)))

    with pytest.raises(DomainError):
        await OfferEditor(keitaro, FakeLog()).save(
            CAMPAIGN_ID, expected=shares((1, 100)), offer_ids=[]
        )

    assert "update_offer_flow" not in keitaro.calls


async def test_save_fails_when_campaign_has_no_offer_flow() -> None:
    keitaro = keitaro_with((), flow_id=None)

    with pytest.raises(DomainError):
        await OfferEditor(keitaro, FakeLog()).save(CAMPAIGN_ID, expected=(), offer_ids=[1])
