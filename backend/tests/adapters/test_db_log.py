from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.db.log import SqlCampaignLog
from app.adapters.db.models import Base, CampaignRow, OfferChangeRow
from app.domain.campaign_name import CampaignName
from app.domain.countries import parse_countries
from app.domain.offers import OfferSet, diff
from app.domain.plan import build_campaign_plan
from tests.helpers import PLACEMENT, shares

PLAN = build_campaign_plan(
    CampaignName("test_kondrashin_c1"),
    parse_countries(["AU", "RO"]),
    18813,
    PLACEMENT,
)


async def rows[T](sessions: async_sessionmaker[AsyncSession], model: type[T]) -> list[T]:
    async with sessions() as session:
        return list((await session.scalars(select(model).order_by(model.id))).all())


async def test_logs_created_campaign(sessions: async_sessionmaker[AsyncSession]) -> None:
    await SqlCampaignLog(sessions).campaign_created(217026, PLAN)

    [row] = await rows(sessions, CampaignRow)
    assert (row.keitaro_id, row.name, row.geo, row.offer_ids) == (
        217026,
        "test_kondrashin_c1",
        ["AU", "RO"],
        [18813],
    )
    assert (row.status, row.error) == ("created", None)
    assert row.created_at is not None


async def test_logs_failures_with_and_without_keitaro_id(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    log = SqlCampaignLog(sessions)

    await log.campaign_failed(None, PLAN, "create_campaign упал")
    await log.campaign_failed(None, PLAN, "снова упал")
    await log.campaign_failed(217027, PLAN, "поток не создался")

    assert [(r.keitaro_id, r.status, r.error) for r in await rows(sessions, CampaignRow)] == [
        (None, "failed", "create_campaign упал"),
        (None, "failed", "снова упал"),
        (217027, "failed", "поток не создался"),
    ]


async def test_logs_offer_changes_for_any_campaign(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    log = SqlCampaignLog(sessions)
    first = diff(shares((1, 70), (2, 30)), OfferSet.evenly([2, 3, 4]).shares)
    second = diff(first.after, OfferSet.evenly([2]).shares)

    # Кампании 5 нет в campaigns: редактор открывает и созданные вне приложения.
    await log.offers_changed(5, first)
    await log.offers_changed(5, second)

    [one, two] = await rows(sessions, OfferChangeRow)
    assert one.keitaro_id == two.keitaro_id == 5
    assert one.before == [{"offer_id": 1, "share": 70}, {"offer_id": 2, "share": 30}]
    assert one.after == [
        {"offer_id": 2, "share": 33},
        {"offer_id": 3, "share": 33},
        {"offer_id": 4, "share": 34},
    ]
    assert two.before == one.after
    assert two.after == [{"offer_id": 2, "share": 100}]
    assert one.changed_at is not None


async def test_migrations_match_models(test_db_url: str) -> None:
    engine = create_async_engine(test_db_url)
    async with engine.connect() as conn:
        changes = await conn.run_sync(
            lambda sync: compare_metadata(MigrationContext.configure(sync), Base.metadata)
        )
    await engine.dispose()

    assert changes == []


async def test_reads_offer_history_newest_first(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    log = SqlCampaignLog(sessions)
    first = diff(shares((1, 100)), OfferSet.evenly([1, 2]).shares)
    second = diff(first.after, OfferSet.evenly([2]).shares)
    await log.offers_changed(5, first)
    await log.offers_changed(6, diff((), OfferSet.evenly([9]).shares))
    await log.offers_changed(5, second)

    history = await log.offer_history(5)

    assert [e.change for e in history] == [second, first]
    assert history[0].changed_at >= history[1].changed_at
