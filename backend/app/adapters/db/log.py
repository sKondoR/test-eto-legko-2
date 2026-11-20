"""CampaignLog поверх Postgres."""

from collections.abc import Sequence
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import Base, CampaignRow, OfferChangeRow
from app.domain.offers import OfferChange, OfferSet, OfferShare, diff
from app.domain.plan import CampaignPlan
from app.domain.ports import OfferHistoryEntry


class SqlCampaignLog:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def campaign_created(self, keitaro_id: int, plan: CampaignPlan) -> None:
        await self._add(_campaign_row(keitaro_id, plan, "created", None))

    async def campaign_failed(self, keitaro_id: int | None, plan: CampaignPlan, error: str) -> None:
        await self._add(_campaign_row(keitaro_id, plan, "failed", error))

    async def offers_changed(self, keitaro_id: int, change: OfferChange) -> None:
        await self._add(
            OfferChangeRow(
                keitaro_id=keitaro_id,
                before=_shares_json(change.before),
                after=_shares_json(change.after),
            )
        )

    async def offer_history(self, keitaro_id: int) -> list[OfferHistoryEntry]:
        query = (
            select(OfferChangeRow)
            .where(OfferChangeRow.keitaro_id == keitaro_id)
            .order_by(OfferChangeRow.changed_at.desc(), OfferChangeRow.id.desc())
        )
        async with self._sessions() as session:
            rows = (await session.scalars(query)).all()
        # after всегда записан из OfferSet, поэтому собирается обратно без ошибок.
        return [
            OfferHistoryEntry(r.changed_at, diff(_shares(r.before), OfferSet(_shares(r.after))))
            for r in rows
        ]

    async def _add(self, row: Base) -> None:
        async with self._sessions.begin() as session:
            session.add(row)


def _campaign_row(
    keitaro_id: int | None,
    plan: CampaignPlan,
    status: Literal["created", "failed"],
    error: str | None,
) -> CampaignRow:
    return CampaignRow(
        keitaro_id=keitaro_id,
        name=plan.name.value,
        geo=[c.value for c in plan.geo_flow.countries],
        offer_ids=list(plan.offer_flow.offers.offer_ids),
        status=status,
        error=error,
    )


def _shares_json(shares: Sequence[OfferShare]) -> list[dict[str, int]]:
    return [{"offer_id": s.offer_id, "share": s.share} for s in shares]


def _shares(items: list[dict[str, int]]) -> tuple[OfferShare, ...]:
    return tuple(OfferShare(i["offer_id"], i["share"]) for i in items)
