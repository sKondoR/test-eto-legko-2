# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Test assignment (see `TASK.md`): a web wrapper over the Keitaro ad tracker (`https://tlgk.host`, Keitaro 10.3.x).

1. **Campaign creator** — takes name, geo (one or more ISO country codes) and a Keitaro offer; creates a campaign with two flows.
2. **Campaign editor** — adds/removes offers in an existing campaign's offer flow; shares must be correct.

Submitted as the public GitHub repo `sKondoR/test-eto-legko-2`; reviewers run it **locally only** from README (no cloud deploy). Required stack: FastAPI + SQLAlchemy, README must cover migrations and launch.

> Status: design agreed, scaffolding in progress. Update this file and README when commands or structure change.

## Layout and commands

```
/                       pnpm workspace (pnpm 12.16.1 via corepack, Node >=24)
├─ apps/web/            Svelte 5 + Vite + TypeScript + Tailwind, SPA (no SvelteKit)
├─ packages/api-types/  TS types generated from FastAPI OpenAPI (openapi-typescript)
├─ backend/             Python 3.13, uv, FastAPI + SQLAlchemy + Alembic, Postgres
└─ docker-compose.yml   db (Postgres) + app (multi-stage: node:24-alpine builds web → FastAPI serves dist)
```

- `pnpm dev` — uvicorn + Vite together; Vite proxies `/api` to uvicorn.
- `pnpm gen:api` — dump OpenAPI via `python -m app.openapi_dump` (no server needed) and regenerate `packages/api-types` (run after changing API schemas).
- `pnpm lint` — ruff + prettier + svelte-check.
- `docker compose up db` — Postgres only (for running backend via uv); `docker compose up` — whole app.
- Migrations: `pnpm db:migrate` (= `uv run --directory backend alembic upgrade head`); new one: `uv run --directory backend alembic revision --autogenerate -m "..."`. Migrations live in `backend/migrations/` (not `alembic/`: that name shadows the `alembic` package for isort); `migrations/env.py` takes the URL from `config.attributes["url"]` (tests) or `DATABASE_URL`.
- Postgres listens on host port **5434** (5432/5433 are often taken by other local Postgres instances).
- Tests: `pnpm test` (needs `docker compose up -d db`: DB tests migrate `keitaro_test` down to base and up to head, then truncate per test); backend only `uv run --directory backend pytest` (single: `... pytest tests/domain/test_shares.py::test_name`); web: `pnpm --filter web test` (vitest).

## Backend architecture ("fat domain")

Dependencies point one way: `api → services → domain ← adapters`.

- `domain/` — pure logic, no IO; defines ports (`Protocol`, `domain/ports.py`): `KeitaroPort`, `CampaignLog`. Errors (`domain/errors.py`): `DomainError` (rule broken → 422), `KeitaroError` (adapter/API failure → 502), `NotFoundError(KeitaroError)` (campaign missing in Keitaro → 404; only `get_campaign` raises it, any other Keitaro 404 stays a 502), `ConflictError` (flow changed in Keitaro meanwhile → 409); all messages are Russian and shown to the user. `app/main.py` maps them to HTTP codes with body `{"detail": "..."}`; FastAPI validation errors (422) and unexpected errors (500, logged) use the same shape with a Russian string, so the UI can always toast `detail`.
- The journal (`CampaignLog`) is secondary to Keitaro: `SqlCampaignLog` logs DB failures and never raises (`offer_history` returns `[]`), so a Postgres outage does not fail a create or save that already went through in Keitaro.
- `services/` — use cases (create campaign, change offers); tested with in-memory fakes of the ports.
- `adapters/keitaro/` — async `httpx2` client implementing `KeitaroPort`; transport is injected, tests pass `httpx2.MockTransport` (no respx: it supports only legacy `httpx`).
- `adapters/db/` — SQLAlchemy models/repositories; tests use a separate Postgres test DB.
- `domain/` and `services/` are written test-first (red-green-refactor).

Domain rules:

- `distribute_shares(n)`: 100 split evenly, remainder goes to the **last** offer (3 → 33/33/34). Same function duplicated in TS (`apps/web`) for instant preview; pytest and vitest cover the same cases.
- `CampaignName`: must start with `test_kondrashin_`, chars `[a-z0-9_]`; UI shows the prefix as fixed.
- `CountryCode`: ISO 3166-1 alpha-2 from a static list.
- `OfferSet` is what we **write** to Keitaro: ordered `OfferShare(offer_id, share)`, never empty, no duplicates, each share 0..100, sum = 100; built with `OfferSet.evenly(ids)` from the editor's final offer list (no separate add/remove on the backend). What we **read** from Keitaro stays a plain `tuple[OfferShare, ...]` with no validation (it may be hand-edited, empty or broken) so the editor can always open and repair a campaign; `is_even_split(shares)` tells the UI to warn that saving overwrites manual shares (remainder position doesn't matter); the editor also reports a flow as not even when `CampaignState.disabled_offer_ids` is non-empty (offers disabled in Keitaro keep a share but get no traffic). `diff(before_from_keitaro, after: OfferSet)` feeds `offer_changes`. All rule violations raise `DomainError` (Russian message shown to the user).
- `build_campaign_plan` returns Keitaro-agnostic `CampaignPlan` (`Placement` IDs, `GeoRedirectFlow`, `OfferFlow`); the Keitaro adapter maps it to API payloads.

Campaign shape (matches the reference screenshots in `TASK.md`):

- Domain / group / traffic source come from `.env` **by name** (`in.posdk.xyz`, `FORTESTS`, `FORTESTS`), resolved to IDs via `GET /domains`, `GET /groups?type=campaigns`, `GET /traffic_sources`. The names are Keitaro adapter config: `KeitaroPort.resolve_placement()` takes no arguments, and the adapter resolves the IDs once and caches them.
- Flow 1: `regular`, position 1, filter `{name: "country", mode: "accept", payload: [geo…]}`, `schema: "redirect"`, `action_type: "http"`, `action_payload: "https://google.com"`.
- Flow 2: `default`, position 2, `schema: "landings"`, `action_type: "http"`, offers `[{offer_id, share}]`. The editor changes only this flow; flow 1 is read-only. The editor opens and saves only campaigns whose name starts with `test_kondrashin_` (`is_ours`); other candidates' campaigns in the tracker must never be touched.
- Creation is several API calls; if a flow fails, the service archives the campaign (`DELETE /campaigns/{id}`) and logs status `failed`.
- Editor saves on an explicit "Save"; before saving the service re-reads the flow and returns 409 if offers changed in Keitaro meanwhile.

DB tables (`adapters/db/models.py`, written by `SqlCampaignLog`): `campaigns` (every creation attempt: `status` `created`/`failed`, `error`, `keitaro_id` NULL when Keitaro never created it; geo and offer IDs stored as arrays) and `offer_changes` (before → after as JSONB `[{offer_id, share}]`; added/removed are derived from them; shown as history in the editor). Both store the Keitaro campaign ID as `keitaro_id`; `offer_changes` has no foreign key to `campaigns`, because the editor also opens `test_kondrashin_*` campaigns created outside the app.

## Our API (`app/api/routes.py`, wiring in `app/main.py` lifespan)

- `GET /api/config` — name prefix, `DEFAULT_GEO`, ISO country list.
- `GET /api/offers` — Keitaro offers (`KeitaroPort.list_offers`).
- `GET /api/campaigns` — our `test_kondrashin_*` campaigns; `POST /api/campaigns` `{name_suffix, countries, offer_id}` → 201 `{id}`.
- `GET /api/campaigns/{id}` — editor view: geo, offers, `disabled_offer_ids`, `is_even`, history (`CampaignLog.offer_history`, newest first).
- `PUT /api/campaigns/{id}/offers` `{expected, offer_ids}` → `{offers}`; `expected` is what the editor showed, a mismatch gives 409.
- Route tests put fakes into `app.state` and use `TestClient(app)` without `with`, so the lifespan (real Keitaro and Postgres) does not run.

## Keitaro Admin API

- Base `{KEITARO_URL}/admin_api/v1`, header `Api-Key`. Spec: `https://admin-api.docs.keitaro.io/openapi.json`.
- `GET /campaigns` has only `offset`/`limit` — filter by the `test_kondrashin_` prefix on our side.
- Cloudflare in front of the tracker answers 403 `error code: 1010` to library User-Agents such as `Python-urllib`: the adapter sends its own `User-Agent`.
- `POST /campaigns` needs `name` and a unique `alias` (we generate it); `POST /streams` returns the created flow with `id`.
- `PUT /streams/{id}` updates only the keys sent. With `offers` it replaces the whole array: offers missing from it are removed, `[]` clears the flow. An offer that stays keeps its row and its `state` even when `state` is not sent, so we never send `state`; new offers get `active`.
- `DELETE /campaigns/{id}` moves the campaign to the archive (`state: "deleted"`); after that `GET /campaigns/{id}` returns a 404 nginx HTML page, not JSON.
- The API key reads offers but cannot create them (`POST /offers` → 403 "no permission … Offers"); the tracker has one offer (18813). The tracker has only the domain `kylovoa.com`.
- Browser never calls Keitaro directly — only our `/api`.

## Environment

`.env` (template `.env.example`): `KEITARO_URL`, `KEITARO_API_KEY`, `KEITARO_DOMAIN`, `KEITARO_GROUP`, `KEITARO_SOURCE`, `DEFAULT_GEO` (comma-separated, validated at startup, exposed to the UI via `GET /api/config`), Postgres connection settings. `LOGIN`/`PASSWORD` are only for a human logging into the Keitaro admin.

## Conventions

- UI text is in Russian; errors shown as toasts; buttons disabled while a request is in flight.
- Keep README current with setup/run steps (corepack enable, versions, `.env`, DB, migrations, both run modes) in the same change that alters them.

## Git workflow

- `main` changes only through pull requests: never commit or push directly to `main`.
- One branch per task (`feat/…`, `fix/…`, `chore/…`, `docs/…`), cut from an up-to-date `main`; open the PR with `gh pr create`.
- Before opening a PR: `pnpm lint` and `pnpm test` pass, README/CLAUDE.md updated if commands or setup changed.
- Merge only after the user's explicit ok.
