# Aviation CAMO & MRO Platform (Foundation)

**Version:** GitHub `main` (rolling) — see `RELEASE_NOTES.md` for history

This repository is a *foundation skeleton* for a multi-tenant CAMO + MRO + Logistics SaaS platform.
No business logic is implemented yet; the goal is to provide structure, documentation, and a runnable scaffold.

Staging używa overlay: `infra/staging/docker-compose.staging.yml`.

## Documentation
- OPS / Production server access & deployment: `docs/03_ops/SERVER_AND_DEPLOYMENT.md`
- PO (non-technical) production workflow summary: `docs/00_product/PO_PROD_WORKFLOW.md`

## Konfiguracja ENV
- Realne pliki `.env` nie są commitowane.
- Szablony znajdują się w:
  - `infra/local/env.example`
  - `infra/staging/env.example`
  - `infra/prod/env.example`

## Quick start (Local / Windows)
1. Install Docker Desktop
2. From repository root run:
   - `start_and_test.bat`

## Staging / Production start (Linux)
System uruchamiany jednym, docelowym entrypointem:

```bash
bash scripts/start_system.sh
```

## Release workflow (GitHub)
- Single cumulative changelog: `RELEASE_NOTES.md` (append-only).
- Semantic versioning: `vX.Y.Z` (early dev uses `v0.x.y`).
- Each release is a **single ZIP** attached to a GitHub Release with matching tag.
- Canonical procedure is documented in: `docs/03_ops/RELEASING_GITHUB.md`.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-11 — EPIC0B B1 (schema-per-tenant) E2E status

**What is now proven working (PROD / public HTTPS):**
- Domains + TLS via reverse proxy: `app.*`, `api.*`, `auth.*`.
- UI performs **OIDC Authorization Code + PKCE** against Keycloak.
- API enforces **RBAC** and **tenant routing**.

**Tenant routing (runtime):**
- Primary: `tenant_id` claim in access token (target state for PROD).
- Admin override: `X-Tenant-Id` header (only for `PLATFORM_ADMIN`).
- Debug override (temporary / non-prod): `X-Debug-Tenant-Id` when `DEBUG_TENANT_HEADER=true`.

**Operational note:**
- Keep `DEBUG_TENANT_HEADER=false` in production after verification; use debug header only as a controlled E2E bootstrap.


---
## ADDENDUM 2026-01-14 — EPIC12 closure (FRONTEND AUTH / OIDC / TENANT FLOW)

**Proven working (PROD):**
- UI login via **OIDC Authorization Code + PKCE** (`aviation-ui`) without manual tokens.
- Token lifecycle: controlled UX on expiry/401 (**Session expired → Login**); no silent refresh.
- Tenant propagation: UI sends `X-Tenant-Id`; API returns diagnostics headers (`X-Tenant-Id`, `X-Tenant-Schema`, `X-Tenant-Source`).

**Operational constraints:**
- Public client → expiry requires **re-login** (expected).
- DEV bypass headers are **local-only** (must not be enabled in PROD).

## Environment (local-first)

- Strategy: `docs/environment/ENV_STRATEGY.md`
- DR / backups: `docs/environment/DR_BACKUP_PLAN.md`

Quick start (local):
- copy `.env.example` → `.env.local` and fill (do not commit)
- run: `bash scripts/bootstrap_local.sh .env.local`

## UI Hotfix: Maintenance Events require `aircraft_id` (server hotfix)

**Date:** 2026-01-14  
**Problem:** UI performed `GET /v1/maintenance-events` without required query parameter and API returned `422` (missing/invalid `aircraft_id`).  
**Fix (web UI):** UI now loads aircraft first (`GET /v1/aircraft`) and then calls:
- `GET /v1/maintenance-events?aircraft_id=<UUID>`

**Current limitation (hotfix scope):**
- UI selects **first aircraft** returned by `/v1/aircraft` to build the query parameter.
- Target behaviour (next iteration): add aircraft selector + persist selection (localStorage).

**Deploy / rebuild (Docker Compose):**
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker
docker compose build web
docker compose up -d --no-deps web
docker compose exec -T web sh -lc 'grep -n "maintenance-events?aircraft_id" /app/app.js | head -5'
```


### UI Tenant Context – Current Model

The UI **does not assume** a pre‑existing tenant context.

On first authenticated load:
1. UI calls `GET /v1/tenants` (Bearer token only).
2. Tenant is deterministically selected and stored in `localStorage`.
3. All domain calls (`/v1/aircraft`, `/v1/maintenance-events`, etc.) include `x-tenant-id`.

This design intentionally decouples UI startup from backend session‑state and prevents init‑storm patterns.

---
## ADDENDUM 2026-01-15 — DMS (Document Management System)

- DMS confirmed as **core module** for regulatory documents (CAMO/MRO/STORES).
- Document is a domain object with lifecycle and signatures; attachments are secondary artifacts.
- Baseline architecture: `docs/01_architecture/dms_overview.md`.

