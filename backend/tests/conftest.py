from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import ROOT, get_settings

# Создаётся при первом запуске контейнера: docker/create-test-db.sql.
TEST_DB = "keitaro_test"
# Фикстура стирает схему и данные, поэтому работает только с локальным Postgres.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """База keitaro_test со схемой из миграций. Сначала откат: так проверяется и downgrade."""
    url = make_url(get_settings().database_url).set(database=TEST_DB)
    if url.host not in LOCAL_HOSTS:
        pytest.fail(
            f"Тесты БД стирают {TEST_DB}, а DATABASE_URL указывает на {url.host!r}. "
            "Запускайте их только с локальным Postgres (docker compose up -d db).",
            pytrace=False,
        )
    url_str = url.render_as_string(hide_password=False)
    config = Config(ROOT / "backend" / "alembic.ini")
    config.attributes["url"] = url_str
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return url_str


@pytest.fixture
async def sessions(test_db_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE campaigns, offer_changes RESTART IDENTITY"))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
