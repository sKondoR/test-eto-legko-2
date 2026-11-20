import json
from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest

from app.adapters.keitaro.client import PAGE_SIZE, USER_AGENT, KeitaroClient
from app.domain.campaign_name import CampaignName
from app.domain.countries import CountryCode
from app.domain.errors import KeitaroError
from app.domain.offers import OfferSet
from app.domain.plan import GeoRedirectFlow, OfferFlow, Placement
from app.domain.ports import CampaignState, CampaignSummary
from tests.helpers import shares

API = "/admin_api/v1"
PLACEMENT = Placement(domain_id=1813, group_id=10332, traffic_source_id=836)

# Сокращённые ответы живого Keitaro (проба 2026-11-20).
DIRECTORIES = {
    ("GET", "/domains"): [{"id": 1813, "name": "kylovoa.com"}],
    ("GET", "/groups"): [
        {"id": 9799, "name": "VZ adrobot test", "type": "campaigns"},
        {"id": 10332, "name": "FORTESTS", "type": "campaigns"},
    ],
    ("GET", "/traffic_sources"): [{"id": 836, "name": "FORTESTS"}],
}
GEO_STREAM = {
    "id": 1333321,
    "type": "regular",
    "position": 1,
    "filters": [{"name": "country", "mode": "accept", "payload": ["AU", "RO"]}],
    "offers": [],
}
OFFER_STREAM = {
    "id": 1333322,
    "type": "default",
    "position": 2,
    "filters": [],
    "offers": [
        {"id": 1, "offer_id": 18813, "share": 70, "state": "active"},
        {"id": 2, "offer_id": 3749, "share": 30, "state": "disabled"},
    ],
}


class KeitaroStub:
    """Обработчик для MockTransport: отвечает по таблице маршрутов и записывает запросы."""

    def __init__(self, routes: dict[tuple[str, str], Any]) -> None:
        self.routes = routes
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        answer = self.routes[(request.method, request.url.path.removeprefix(API))]
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, httpx2.Response):
            return answer
        return httpx2.Response(200, json=answer)

    def sent(self, method: str, path: str) -> list[Any]:
        return [
            json.loads(r.content)
            for r in self.requests
            if r.method == method and r.url.path == API + path
        ]


def make_client(stub: KeitaroStub, domain: str = "kylovoa.com") -> KeitaroClient:
    return KeitaroClient(
        "https://tlgk.host/",
        "secret-key",
        domain=domain,
        group="FORTESTS",
        source="FORTESTS",
        transport=httpx2.MockTransport(stub),
    )


@pytest.fixture
def fake() -> KeitaroStub:
    return KeitaroStub(dict(DIRECTORIES))


@pytest.fixture
async def client(fake: KeitaroStub) -> AsyncIterator[KeitaroClient]:
    client = make_client(fake)
    yield client
    await client.aclose()


async def test_resolves_placement_by_name_once(client: KeitaroClient, fake: KeitaroStub) -> None:
    assert await client.resolve_placement() == PLACEMENT
    assert await client.resolve_placement() == PLACEMENT

    assert len(fake.requests) == 3
    groups = next(r for r in fake.requests if r.url.path.endswith("/groups"))
    assert groups.url.params["type"] == "campaigns"
    for r in fake.requests:
        assert r.url.host == "tlgk.host"
        assert r.url.path.startswith(API + "/")
        assert r.headers["Api-Key"] == "secret-key"
        assert r.headers["User-Agent"] == USER_AGENT


async def test_unknown_domain_is_reported_by_name(fake: KeitaroStub) -> None:
    client = make_client(fake, domain="in.posdk.xyz")
    with pytest.raises(KeitaroError, match="in.posdk.xyz"):
        await client.resolve_placement()
    await client.aclose()


async def test_creates_campaign_in_placement(client: KeitaroClient, fake: KeitaroStub) -> None:
    fake.routes[("POST", "/campaigns")] = {"id": 217026, "type": "position"}

    campaign_id = await client.create_campaign(CampaignName("test_kondrashin_c1"), PLACEMENT)

    assert campaign_id == 217026
    [body] = fake.sent("POST", "/campaigns")
    assert body["name"] == "test_kondrashin_c1"
    assert body["alias"]
    assert (body["domain_id"], body["group_id"], body["traffic_source_id"]) == (1813, 10332, 836)


async def test_geo_flow_redirects_countries_to_google(
    client: KeitaroClient, fake: KeitaroStub
) -> None:
    fake.routes[("POST", "/streams")] = {"id": 1}

    await client.create_geo_flow(7, GeoRedirectFlow((CountryCode("AU"), CountryCode("RO"))))

    [body] = fake.sent("POST", "/streams")
    assert body == {
        "campaign_id": 7,
        "type": "regular",
        "name": "Geo redirect",
        "position": 1,
        "schema": "redirect",
        "action_type": "http",
        "action_payload": "https://google.com",
        "filters": [{"name": "country", "mode": "accept", "payload": ["AU", "RO"]}],
    }


async def test_offer_flow_is_default_with_offer_shares(
    client: KeitaroClient, fake: KeitaroStub
) -> None:
    fake.routes[("POST", "/streams")] = {"id": 2}

    await client.create_offer_flow(7, OfferFlow(OfferSet.evenly([18813])))

    [body] = fake.sent("POST", "/streams")
    assert body["campaign_id"] == 7
    assert (body["type"], body["position"], body["schema"]) == ("default", 2, "landings")
    assert body["offers"] == [{"offer_id": 18813, "share": 100}]


async def test_archives_campaign_with_delete(client: KeitaroClient, fake: KeitaroStub) -> None:
    fake.routes[("DELETE", "/campaigns/7")] = [{"id": 7, "state": "deleted"}]

    await client.archive_campaign(7)

    assert [(r.method, r.url.path) for r in fake.requests] == [("DELETE", API + "/campaigns/7")]


async def test_lists_campaigns_across_pages(client: KeitaroClient, fake: KeitaroStub) -> None:
    total = PAGE_SIZE + 2

    def page(request: httpx2.Request) -> list[dict[str, Any]]:
        offset, limit = int(request.url.params["offset"]), int(request.url.params["limit"])
        return [{"id": i, "name": f"c{i}"} for i in range(offset, min(offset + limit, total))]

    fake.routes[("GET", "/campaigns")] = page

    campaigns = await client.list_campaigns()

    assert len(campaigns) == total
    assert campaigns[-1] == CampaignSummary(total - 1, f"c{total - 1}")
    assert len(fake.requests) == 2


async def test_reads_campaign_geo_and_offer_flow(client: KeitaroClient, fake: KeitaroStub) -> None:
    fake.routes[("GET", "/campaigns/7")] = {"id": 7, "name": "test_kondrashin_c1"}
    fake.routes[("GET", "/campaigns/7/streams")] = [GEO_STREAM, OFFER_STREAM]

    campaign = await client.get_campaign(7)

    assert campaign == CampaignState(
        id=7,
        name="test_kondrashin_c1",
        geo_countries=("AU", "RO"),
        offer_flow_id=1333322,
        offers=shares((18813, 70), (3749, 30)),
    )


async def test_reads_campaign_without_flows(client: KeitaroClient, fake: KeitaroStub) -> None:
    fake.routes[("GET", "/campaigns/7")] = {"id": 7, "name": "test_kondrashin_c1"}
    fake.routes[("GET", "/campaigns/7/streams")] = []

    campaign = await client.get_campaign(7)

    assert (campaign.geo_countries, campaign.offer_flow_id, campaign.offers) == ((), None, ())


async def test_update_sends_full_offer_list_only(client: KeitaroClient, fake: KeitaroStub) -> None:
    fake.routes[("PUT", "/streams/1333322")] = OFFER_STREAM

    await client.update_offer_flow(1333322, OfferSet.evenly([1, 2, 3]))

    [body] = fake.sent("PUT", "/streams/1333322")
    assert body == {
        "offers": [
            {"offer_id": 1, "share": 33},
            {"offer_id": 2, "share": 33},
            {"offer_id": 3, "share": 34},
        ]
    }


@pytest.mark.parametrize(
    ("response", "detail"),
    [
        (httpx2.Response(403, json={"error": "You have no permission"}), "You have no permission"),
        (httpx2.Response(403, text="error code: 1010\n"), "error code: 1010"),
        (httpx2.Response(404, html="<html><h1>404 Not Found</h1></html>"), "404 Not Found"),
        (httpx2.Response(500), "Internal Server Error"),
    ],
)
async def test_http_errors_become_keitaro_errors(
    client: KeitaroClient, fake: KeitaroStub, response: httpx2.Response, detail: str
) -> None:
    fake.routes[("DELETE", "/campaigns/7")] = response

    with pytest.raises(KeitaroError, match=str(response.status_code)) as error:
        await client.archive_campaign(7)

    assert detail in str(error.value)


async def test_network_failure_becomes_keitaro_error(
    client: KeitaroClient, fake: KeitaroStub
) -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    fake.routes[("DELETE", "/campaigns/7")] = refuse

    with pytest.raises(KeitaroError, match="недоступен"):
        await client.archive_campaign(7)
