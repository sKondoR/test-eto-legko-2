# Кампании Keitaro

Обёртка над трекером Keitaro (тестовое задание, см. [`TASK.md`](TASK.md)):

1. **Создаватор кампаний** — по имени, гео и офферу создаёт кампанию с двумя потоками: поток 1 отправляет трафик из выбранных стран на Google, поток 2 — на офферы.
2. **Редактор кампании** — добавляет и удаляет офферы во втором потоке; доли делятся поровну, остаток получает последний оффер (3 оффера → 33/33/34).

Стек: FastAPI + SQLAlchemy + Alembic + Postgres (бэкенд), Svelte 5 + Vite + TypeScript + Tailwind (фронт), pnpm workspace.

## Что нужно установить

| Инструмент | Версия       | Как поставить                                             |
| ---------- | ------------ | --------------------------------------------------------- |
| Node.js    | 24+          | https://nodejs.org                                        |
| pnpm       | 12.16.1      | `corepack enable` (pnpm возьмёт версию из `package.json`) |
| uv         | 0.10+        | https://docs.astral.sh/uv/ — Python 3.13 uv скачает сам   |
| Docker     | любая свежая | для Postgres                                              |

## Настройка

1. Скопируйте шаблон переменных:
   ```sh
   cp .env.example .env
   ```
2. Впишите в `.env` ключ API: админка Keitaro → Профиль → API ключи → `KEITARO_API_KEY`.
   Остальные значения в шаблоне уже рабочие (домен `in.posdk.xyz`, группа и источник `FORTESTS`, страна по умолчанию `AU`).
3. Поставьте зависимости:
   ```sh
   corepack enable
   pnpm install
   uv sync --directory backend
   ```
4. Поднимите Postgres (заодно создаётся база `keitaro_test` для тестов):
   ```sh
   docker compose up -d db
   ```
   База `keitaro_test` создаётся только при первом запуске, на пустом томе. Если том `pgdata` остался от старой версии без неё, пересоздайте его: `docker compose down -v && docker compose up -d db`.

## Запуск для разработки

```sh
pnpm dev
```

Бэкенд — http://127.0.0.1:8000 (Swagger: `/docs`), фронт — http://localhost:5173 (запросы `/api` проксируются на бэкенд).

## Проверки

```sh
pnpm test   # pytest (бэкенд) + vitest (фронт)
pnpm lint   # ruff + prettier + svelte-check
```

Один тест: `uv run --directory backend pytest tests/test_health.py::test_health`.

## Ограничения тестового трекера

- В трекере один оффер (18813), а ключ API не может создавать офферы (`POST /offers` → 403). Поэтому на живых данных редактор работает с одним оффером. Деление долей (3 оффера → 33/33/34) проверяют тесты (`pnpm test`) и показывает превью долей в редакторе.
- Перед трекером стоит Cloudflare: он отклоняет запросы с User-Agent библиотек (`error code: 1010`). Бэкенд отправляет свой User-Agent.

## Типы API для фронта

Типы в `packages/api-types` генерируются из OpenAPI-схемы FastAPI. После изменения API выполните:

```sh
pnpm gen:api
```
