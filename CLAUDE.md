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
- Migrations: `pnpm db:migrate` (= `uv run --directory backend alembic upgrade head`).
- Tests: `pnpm test`; backend only `uv run --directory backend pytest` (single: `... pytest tests/domain/test_shares.py::test_name`); web: `pnpm --filter web test` (vitest).

## Backend architecture ("fat domain")

Dependencies point one way: `api → services → domain ← adapters`.

- `domain/` — pure logic, no IO; defines ports (`Protocol`): `KeitaroPort`, `CampaignLog`.
- `services/` — use cases (create campaign, change offers); tested with in-memory fakes of the ports.
- `adapters/keitaro/` — async `httpx2` client implementing `KeitaroPort`; transport is injected, tests pass `httpx2.MockTransport` (no respx: it supports only legacy `httpx`).
- `adapters/db/` — SQLAlchemy models/repositories; tests use a separate Postgres test DB.
- `domain/` and `services/` are written test-first (red-green-refactor).

Domain rules:

- `distribute_shares(n)`: 100 split evenly, remainder goes to the **last** offer (3 → 33/33/34). Same function duplicated in TS (`apps/web`) for instant preview; pytest and vitest cover the same cases.
- `CampaignName`: must start with `test_kondrashin_`, chars `[a-z0-9_]`; UI shows the prefix as fixed.
- `CountryCode`: ISO 3166-1 alpha-2 from a static list.
- `OfferSet`: wraps the offer flow as ordered `OfferShare(offer_id, share)`; never empty, no duplicates. Keitaro shares are kept as-is (may be manual, `is_even` tells the UI to warn); the editor sends the final offer list and the backend rebuilds it with `OfferSet.evenly(ids)` (no separate add/remove on the backend). `diff(before, after)` feeds `offer_changes`. All rule violations raise `DomainError` (Russian message shown to the user).
- `build_campaign_plan` returns Keitaro-agnostic `CampaignPlan` (`Placement` IDs, `GeoRedirectFlow`, `OfferFlow`); the Keitaro adapter maps it to API payloads.

Campaign shape (matches the reference screenshots in `TASK.md`):

- Domain / group / traffic source come from `.env` **by name** (`in.posdk.xyz`, `FORTESTS`, `FORTESTS`), resolved to IDs via `GET /domains`, `GET /groups?type=campaigns`, `GET /traffic_sources`.
- Flow 1: `regular`, position 1, filter `{name: "country", mode: "accept", payload: [geo…]}`, HTTP redirect to `https://google.com` (verify exact `action_type` via `GET /streams_actions`).
- Flow 2: `default`, offers `[{offer_id, share}]`. The editor changes only this flow; flow 1 is read-only.
- Creation is several API calls; if a flow fails, the service archives the campaign (`DELETE /campaigns/{id}`) and logs status `failed`.
- Editor saves on an explicit "Save"; before saving the service re-reads the flow and returns 409 if offers changed in Keitaro meanwhile.

DB tables: `campaigns` (campaigns created via the app; geo stored as array) and `offer_changes` (before → after log, shown as history in the editor).

## Keitaro Admin API

- Base `{KEITARO_URL}/admin_api/v1`, header `Api-Key`. Spec: `https://admin-api.docs.keitaro.io/openapi.json`.
- `GET /campaigns` has only `offset`/`limit` — filter by the `test_kondrashin_` prefix on our side.
- PUT updates only the fields sent; always send the full `offers` array for a flow.
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
