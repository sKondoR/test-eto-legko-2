from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import WEB_DIST

app = FastAPI(title="Keitaro campaigns")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Собранный фронт раздаётся тем же сервером (в Docker и после `pnpm build`).
# Монтирование на "/" перекрывает всё, что подключено после него, поэтому оно последнее.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
