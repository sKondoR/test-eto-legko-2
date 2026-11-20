"""CampaignLog поверх Postgres."""

from collections.abc import Sequence
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.models import Base, CampaignRow, OfferChangeRow
from app.domain.offers import OfferChange, OfferShare
from app.domain.plan import CampaignPlan


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
                added=list(change.added),
                removed=list(change.removed),
            )
        )

    async def _add(self, row: Base) -> None:
        async with self._sessions.begin() as session:
            session.add(row)


def _campaign_row(
    keitaro_id: int | None, plan: CampaignPlan, status: str, error: str | None
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
    return [asdict(s) for s in shares]
