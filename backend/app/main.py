from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.log import SqlCampaignLog
from app.adapters.keitaro.client import KeitaroClient
from app.api.routes import router
from app.config import WEB_DIST, get_settings
from app.domain.countries import parse_countries
from app.domain.errors import ConflictError, DomainError, KeitaroError, NotFoundError
from app.services.campaigns import CampaignService
from app.services.offer_editor import OfferEditor

# HTTP-коды ошибок сервисов. Starlette ищет обработчик по MRO, поэтому NotFoundError
# (подкласс KeitaroError) получает свой 404, а не 502.
ERROR_STATUS = {DomainError: 422, NotFoundError: 404, ConflictError: 409, KeitaroError: 502}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Неверный DEFAULT_GEO останавливает запуск, а не всплывает в форме создания.
    app.state.default_geo = parse_countries(settings.default_geo.split(","))
    keitaro = KeitaroClient(
        settings.keitaro_url,
        settings.keitaro_api_key,
        domain=settings.keitaro_domain,
        group=settings.keitaro_group,
        source=settings.keitaro_source,
    )
    engine = create_async_engine(settings.database_url)
    log = SqlCampaignLog(async_sessionmaker(engine, expire_on_commit=False))
    app.state.campaigns = CampaignService(keitaro, log)
    app.state.editor = OfferEditor(keitaro, log)
    yield
    await keitaro.aclose()
    await engine.dispose()


app = FastAPI(title="Keitaro campaigns", lifespan=lifespan)


def _error_handler(status: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=status)

    return handle


for error_class, status in ERROR_STATUS.items():
    app.add_exception_handler(error_class, _error_handler(status))


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)

# Собранный фронт раздаётся тем же сервером (в Docker и после `pnpm build`).
# Монтирование на "/" перекрывает всё, что подключено после него, поэтому оно последнее.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
