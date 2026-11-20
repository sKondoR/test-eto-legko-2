"""KeitaroPort поверх Keitaro Admin API (/admin_api/v1)."""

import asyncio
import secrets
from typing import Any

import httpx2

from app.domain.campaign_name import CampaignName
from app.domain.errors import KeitaroError, NotFoundError
from app.domain.offers import OfferSet, OfferShare
from app.domain.plan import GOOGLE_URL, GeoRedirectFlow, OfferFlow, Placement
from app.domain.ports import CampaignState, CampaignSummary, DomainSummary, OfferSummary

# Cloudflare перед трекером отвечает 403 (error 1010) на User-Agent библиотек вроде Python-urllib.
USER_AGENT = "keitaro-campaigns/0.1"
PAGE_SIZE = 500
# Типы потоков Keitaro: по ним создаём потоки и по ним же узнаём их при чтении.
GEO_FLOW_TYPE = "regular"
OFFER_FLOW_TYPE = "default"


class KeitaroClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        group: str,
        source: str,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx2.AsyncClient(
            base_url=base_url.rstrip("/") + "/admin_api/v1",
            headers={"Api-Key": api_key, "User-Agent": USER_AGENT},
            timeout=15,
            transport=transport,
        )
        self._names = (group, source)
        self._group_and_source: tuple[int, int] | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def resolve_placement(self, domain_id: int) -> Placement:
        # Имена из настроек не меняются, пока процесс жив: ищем ID один раз.
        if self._group_and_source is None:
            group, source = self._names
            groups, sources = await asyncio.gather(
                self._request("GET", "/groups", params={"type": "campaigns"}),
                self._request("GET", "/traffic_sources"),
            )
            self._group_and_source = (
                _id_by_name(groups, group, "группы кампаний"),
                _id_by_name(sources, source, "источника трафика"),
            )
        group_id, traffic_source_id = self._group_and_source
        return Placement(domain_id, group_id, traffic_source_id)

    async def create_campaign(self, name: CampaignName, placement: Placement) -> int:
        campaign = await self._request(
            "POST",
            "/campaigns",
            json={
                "name": name.value,
                "alias": secrets.token_hex(4),
                "domain_id": placement.domain_id,
                "group_id": placement.group_id,
                "traffic_source_id": placement.traffic_source_id,
            },
        )
        return campaign["id"]

    async def create_geo_flow(self, campaign_id: int, flow: GeoRedirectFlow) -> None:
        await self._request(
            "POST",
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": GEO_FLOW_TYPE,
                "name": "Geo redirect",
                "position": 1,
                "schema": "redirect",
                "action_type": "http",
                "action_payload": GOOGLE_URL,
                "filters": [
                    {
                        "name": "country",
                        "mode": "accept",
                        "payload": [c.value for c in flow.countries],
                    }
                ],
            },
        )

    async def create_offer_flow(self, campaign_id: int, flow: OfferFlow) -> None:
        await self._request(
            "POST",
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": OFFER_FLOW_TYPE,
                "name": "Offers",
                "position": 2,
                "schema": "landings",
                "action_type": "http",
                "offers": _offers_payload(flow.offers),
            },
        )

    async def archive_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    async def list_campaigns(self) -> list[CampaignSummary]:
        # Фильтра по имени в API нет: читаем все страницы.
        # Конец — пустая страница: сервер может урезать limit, короткая страница не последняя.
        campaigns: list[CampaignSummary] = []
        while page := await self._request(
            "GET", "/campaigns", params={"offset": len(campaigns), "limit": PAGE_SIZE}
        ):
            campaigns += [CampaignSummary(c["id"], c["name"]) for c in page]
        return campaigns

    async def get_campaign(self, campaign_id: int) -> CampaignState:
        not_found = f"Кампании {campaign_id} нет в Keitaro: её удалили или отправили в архив"
        campaign, streams = await asyncio.gather(
            self._request("GET", f"/campaigns/{campaign_id}", not_found=not_found),
            self._request("GET", f"/campaigns/{campaign_id}/streams", not_found=not_found),
        )
        offer_flow = next((s for s in streams if s["type"] == OFFER_FLOW_TYPE), None)
        offers = offer_flow["offers"] if offer_flow else []
        return CampaignState(
            id=campaign["id"],
            name=campaign["name"],
            geo_countries=_geo_countries(streams),
            offer_flow_id=offer_flow["id"] if offer_flow else None,
            offers=tuple(OfferShare(o["offer_id"], o["share"]) for o in offers),
            disabled_offer_ids=tuple(o["offer_id"] for o in offers if o["state"] != "active"),
        )

    async def update_offer_flow(self, flow_id: int, offers: OfferSet) -> None:
        # PUT заменяет весь массив offers. state у оставшихся офферов Keitaro сохраняет сам.
        await self._request("PUT", f"/streams/{flow_id}", json={"offers": _offers_payload(offers)})

    async def list_offers(self) -> list[OfferSummary]:
        return [OfferSummary(o["id"], o["name"]) for o in await self._request("GET", "/offers")]

    async def list_domains(self) -> list[DomainSummary]:
        return [DomainSummary(d["id"], d["name"]) for d in await self._request("GET", "/domains")]

    async def _request(
        self, method: str, path: str, *, not_found: str | None = None, **kwargs: Any
    ) -> Any:
        """not_found — текст NotFoundError на 404. Без него 404 — обычный сбой Keitaro (502):
        например, неверный KEITARO_URL не должен выглядеть для пользователя как «не найдено»."""
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx2.TransportError as error:
            raise KeitaroError(f"Keitaro недоступен: {error}") from error
        if response.status_code == 404 and not_found:
            raise NotFoundError(not_found)
        if response.is_error:
            raise KeitaroError(
                f"Keitaro вернул ошибку {response.status_code} на {method} {path}: "
                f"{_error_detail(response)}"
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise KeitaroError(
                f"Keitaro ответил не JSON на {method} {path}: {response.text.strip()[:200]}"
            ) from error


def _id_by_name(items: list[dict[str, Any]], name: str, what: str) -> int:
    for item in items:
        if item["name"] == name:
            return item["id"]
    raise KeitaroError(f"В Keitaro нет {what} с именем {name!r}")


def _offers_payload(offers: OfferSet) -> list[dict[str, int]]:
    return [{"offer_id": s.offer_id, "share": s.share} for s in offers.shares]


def _geo_countries(streams: list[dict[str, Any]]) -> tuple[str, ...]:
    for stream in streams:
        if stream["type"] != GEO_FLOW_TYPE:
            continue
        for f in stream["filters"]:
            if f["name"] == "country" and f["mode"] == "accept":
                return tuple(f["payload"])
    return ()


def _error_detail(response: httpx2.Response) -> str:
    # Keitaro отдаёт {"error": "..."}; nginx и Cloudflare — HTML или текст.
    try:
        return str(response.json()["error"])
    except (ValueError, KeyError, TypeError):
        return response.text.strip()[:200] or response.reason_phrase
