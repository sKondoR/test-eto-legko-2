from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.domain.countries import parse_countries
from app.domain.ports import CampaignState, OfferSummary
from app.main import app
from app.services.campaigns import CampaignService
from app.services.offer_editor import OfferEditor
from tests.helpers import PLACEMENT, shares
from tests.services.fakes import FakeKeitaro, FakeLog


@pytest.fixture
def keitaro() -> FakeKeitaro:
    return FakeKeitaro(placement=PLACEMENT, offers=[OfferSummary(18813, "Flexacil")])


@pytest.fixture
def client(keitaro: FakeKeitaro) -> Iterator[TestClient]:
    # Без `with TestClient(...)` lifespan не запускается: порты подменяем фейками.
    log = FakeLog()
    app.state.default_geo = parse_countries(["AU"])
    app.state.campaigns = CampaignService(keitaro, log)
    app.state.editor = OfferEditor(keitaro, log)
    yield TestClient(app)


def create(client: TestClient, suffix: str = "c1") -> int:
    response = client.post(
        "/api/campaigns", json={"name_suffix": suffix, "countries": ["au"], "offer_id": 18813}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_config_exposes_prefix_default_geo_and_countries(client: TestClient) -> None:
    config = client.get("/api/config").json()

    assert config["name_prefix"] == "test_kondrashin_"
    assert config["default_geo"] == ["AU"]
    assert len(config["countries"]) == 249
    assert "RO" in config["countries"]


def test_lists_offers(client: TestClient) -> None:
    assert client.get("/api/offers").json() == [{"id": 18813, "name": "Flexacil"}]


def test_creates_and_lists_only_our_campaigns(client: TestClient, keitaro: FakeKeitaro) -> None:
    campaign_id = create(client)
    keitaro.campaigns[1] = CampaignState(1, "test_ivanov_c1", (), None, ())

    assert client.get("/api/campaigns").json() == [
        {"id": campaign_id, "name": "test_kondrashin_c1"}
    ]


def test_domain_error_is_422_with_russian_detail(client: TestClient) -> None:
    response = client.post(
        "/api/campaigns", json={"name_suffix": "Bad Name", "countries": ["AU"], "offer_id": 1}
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Имя кампании")


def test_keitaro_error_is_502(client: TestClient, keitaro: FakeKeitaro) -> None:
    keitaro.fail_on.add("create_offer_flow")

    response = client.post(
        "/api/campaigns", json={"name_suffix": "c1", "countries": ["AU"], "offer_id": 1}
    )

    assert response.status_code == 502
    assert "create_offer_flow" in response.json()["detail"]


def test_editor_shows_campaign(client: TestClient) -> None:
    campaign_id = create(client)

    editor = client.get(f"/api/campaigns/{campaign_id}").json()

    assert editor == {
        "id": campaign_id,
        "name": "test_kondrashin_c1",
        "geo": ["AU"],
        "offers": [{"offer_id": 18813, "share": 100}],
        "disabled_offer_ids": [],
        "is_even": True,
        "history": [],
    }


def test_unknown_campaign_is_404(client: TestClient) -> None:
    response = client.get("/api/campaigns/999")

    assert response.status_code == 404
    assert response.json()["detail"]


def test_foreign_campaign_is_422(client: TestClient, keitaro: FakeKeitaro) -> None:
    keitaro.campaigns[1] = CampaignState(1, "test_ivanov_c1", (), 10, shares((1, 100)))

    assert client.get("/api/campaigns/1").status_code == 422


def test_saves_offers_and_shows_history(client: TestClient) -> None:
    campaign_id = create(client)

    response = client.put(
        f"/api/campaigns/{campaign_id}/offers",
        json={"expected": [{"offer_id": 18813, "share": 100}], "offer_ids": [18813, 2, 3]},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "offers": [
            {"offer_id": 18813, "share": 33},
            {"offer_id": 2, "share": 33},
            {"offer_id": 3, "share": 34},
        ]
    }
    [entry] = client.get(f"/api/campaigns/{campaign_id}").json()["history"]
    assert entry["before"] == [{"offer_id": 18813, "share": 100}]
    assert (entry["added"], entry["removed"]) == ([2, 3], [])
    assert entry["changed_at"]


def test_conflict_is_409(client: TestClient) -> None:
    campaign_id = create(client)

    response = client.put(
        f"/api/campaigns/{campaign_id}/offers",
        json={"expected": [{"offer_id": 1, "share": 100}], "offer_ids": [18813]},
    )

    assert response.status_code == 409
    assert "Обновите страницу" in response.json()["detail"]
