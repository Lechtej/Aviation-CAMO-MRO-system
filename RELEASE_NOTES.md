# AviationCAMO-MRO — Release Notes (cumulative)

## v0.2.42.2 (2026-01-11) — Keycloak Direct Grant unblock + tenant_id claim hardening (docs)

- Keycloak/OIDC: documented + validated fix for `invalid_grant` / `Account is not fully set up` when using `grant_type=password`:
  - clone Direct Grant flow → `direct-grant-no-otp` (OTP + condition disabled)
  - set realm `directGrantFlow` to the cloned flow
  - disable blocking Required Actions (VERIFY_PROFILE / UPDATE_PROFILE / UPDATE_PASSWORD / CONFIGURE_TOTP) in this test environment
- Keycloak/OIDC: confirmed `tenant_id` claim delivered in access token via `oidc-usermodel-attribute-mapper` (attribute `tenant_id` on user + protocol mapper on `aviation-api` client).
- Docs updated (append-only):
  - `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md`
  - `docs/03_ops/SERVER_SMOKE_TEST_KEYCLOAK_OIDC.md`
  - `docs/03_ops/deployment.md`

## v0.2.3.1 (2026-01-09) — Docs reconstruction + GitHub releasing + API import-time hardening notes
- Docs: restored full historical `RELEASE_NOTES.md` and documentation set from last pre-release-cleanup ZIP.
- Docs: added GitHub release procedure (ZIP-first, tags, single changelog).
- Docs: documented canonical runtime import validation for SQLAlchemy models (container-level `import main`).

## v0.2.2 — packaging + docs alignment (2026-01-08)
- Packaging: ZIP now matches GitHub repo root layout (no extra wrapper folder, single `RELEASE_NOTES.md` at repo root).
- Docs: moved `docs/SERVER_SMOKE_TEST_KEYCLOAK_OIDC.md` into `docs/03_ops/` to keep all server/OIDC smoke-test material together.

## v0.2.1 (2026-01-08) — DB baseline packaging

### Docs
- Added server-side, validated walkthrough for **Keycloak HTTP + client_credentials + PLATFORM_ADMIN + tenant bootstrap**:
  - `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md`

> Note: this entry documents the **DB baseline ZIP packaging** and the verified server steps. It does not imply the application code regressed from v0.2.42.

## v0.2.42.1 (2026-01-11)

Dokumentacja / DEV ops:
- Uzupełniono `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md` o procedurę: ustawienie wspólnego hasła dla dummy userów (DEV), naprawa `Account is not fully set up`, przypisanie `PLATFORM_ADMIN`, uruchomienie `_admin/bootstrap`, oraz minimalny test Create/List Aircraft.
- Uzupełniono `docs/03_ops/SERVER_SMOKE_TEST_KEYCLOAK_OIDC.md` o smoke test dla password grant + automatyczny parsing `/openapi.json` + mini-macierz RBAC.
- Uzupełniono `docs/00_product/PO_RBAC_AND_TENANTS_STATUS_v0.2.4.md` o obserwacje RBAC na DEV i rekomendacje backlog.
- Docs: EPIC1 — Work Orders (design-only contract): WO/Tasks/TaskCards, statuses, permission-based RBAC mapping (CAMO/MRO/STORE/B1).

## v0.2.42 (2026-01-06)

### Fixed
- **CORS / UI tester**: API teraz akceptuje żądania z UI uruchomionego na `http://localhost` (dowolny port), dzięki czemu przycisk **Send request** nie kończy się błędem typu „Failed to fetch”.

## v0.2.41 (2026-01-06)

### Fixed
- **UI draft**: naprawione niespójne ID elementów (index.html vs app.js). UI na `http://localhost:3000` działa po starcie stacka.
- UI tester ma teraz prosty, stabilny zestaw akcji: **Ping /docs**, wysyłka requestu do dowolnej ścieżki, opcjonalny Bearer token.

## v0.2.40 (2026-01-06)

### Fixed
- **start_and_test.bat**: naprawiony healthcheck `/docs` (wcześniej w pliku był ucięty fragment komendy PowerShell, co zawsze kończyło się błędem mimo działającego API).
- Healthcheck jest teraz **odporny na wolny start**: do 30 prób z krótkim retry.

## v0.2.39 (2026-01-06)

### Added
- **UI draft (very first)**: minimal static web UI served at `http://localhost:3000` (container `web`) with basic API helpers.

### Changed
- Windows `.bat` scripts no longer depend on `tee` and keep the console open on errors (better for double-click runs).

### Fixed
- Diagnostic script now calls the main script via absolute path (so it works from any current directory).

## v0.2.38

- Consolidated all per-version release notes into this single cumulative file.
- Kept only the latest BAT scripts in the ZIP (start_and_test.bat, start_and_test_DIAG.bat).

## v0.2.28

# AviationCAMO-MRO v0.2.28 — Tenant Isolation (Inventory / Parts)

## Why
A confirmed data leak allowed Tenant B to see `Parts` created by Tenant A via `GET /v1/inventory/parts`.

## Changes
### DB
- `public.parts`
  - added column `tenant_id uuid` (nullable; transitional migration step)
  - added index `idx_parts_tenant_id` on `(tenant_id)`

### API
- All `/v1/inventory/parts*` endpoints are now tenant-scoped.
  - **CREATE** writes `tenant_id` from the resolved tenant context.
  - **LIST** filters by `tenant_id`.
  - **GET/UPDATE/DELETE** only operate within the caller's tenant (otherwise `404`).
- Requests without a resolved tenant context are rejected with `403 Tenant context missing`.

## Notes / Limitations
- `tenant_id` is nullable to allow a safe transition. Records with `tenant_id = NULL` will not be returned by tenant-scoped list queries.
- Existing unique constraint on `part_number` remains global (not per-tenant) in this version.

## How to test (A vs B)
1. Obtain tokens for Tenant A and Tenant B (token must contain `tenant_id` claim or use `X-Tenant-Id` only with `PLATFORM_ADMIN`).
2. Tenant A: `POST /v1/inventory/parts` (create a new part).
3. Tenant B: `GET /v1/inventory/parts`.

Expected: Tenant B does **not** see Tenant A's part.

## # v0.2.29 — PO Guide + BAT cleanup (2026-01-06)
### Added
- PO-friendly guide: `docs/00_product/PO_GUIDE.md`
- Updated Windows helpers: `start_and_test_v0.2.29.bat`, `start_and_test_DIAG_v0.2.29.bat`

### Changed
- Version bump only (no functional changes vs v0.2.28)

### Removed
- Older `start_and_test*.bat` versions from the ZIP (keep only latest)

## v0.2.30

# AviationCAMO-MRO v0.2.30 — Release Notes

## Zmiany funkcjonalne
- **Aircraft: własność + dostęp MRO**
  - Nowe endpointy `/v1/aircraft`:
    - Owner tenant może tworzyć i usuwać samoloty.
    - Owner tenant może nadawać/odbierać dostęp MRO (`/mro-access`).
    - Tenant MRO widzi przypisane samoloty i może aktualizować tylko **status_tech** i **notes**.

## Zmiany techniczne
- Dodano tabele w `public`:
  - `public.aircraft`
  - `public.aircraft_mro_access`
- Dodano dev bootstrap: `POST /v1/aircraft/_admin/bootstrap`.

## Zgodność / kompatybilność
- Zmiany są addytywne (bez migracji istniejących danych).
- Wersja jest przygotowana pod późniejsze, formalne migracje.

## v0.2.31

# AviationCAMO-MRO — Release Notes v0.2.31

Data: 2026-01-06

## Zakres
### Aircraft — Maintenance Events
Dodano obsługę **Maintenance Events** dla samolotów:
- Owner tenant (linia lotnicza) może tworzyć i w pełni aktualizować zdarzenia utrzymaniowe.
- Tenants MRO z aktywnym dostępem do danego samolotu mogą:
  - przeglądać zdarzenia,
  - aktualizować tylko `status` oraz `mro_notes`.

Endpointy:
- `GET /v1/aircraft/{aircraft_id}/maintenance-events`
- `POST /v1/aircraft/{aircraft_id}/maintenance-events`
- `PUT /v1/aircraft/{aircraft_id}/maintenance-events/{event_id}`

## Techniczne
- Nowa tabela w schemacie `public`: `aircraft_maintenance_events`.
- Zaktualizowano `docs/02_api/openapi.yaml`.

## Narzędzia uruchomieniowe (Windows)
- Zaktualizowano pliki `.bat` do wersji v0.2.31.
- Skrypty `.bat` nie zamykają się automatycznie (ułatwia diagnozę).

## v0.2.32

# AviationCAMO-MRO — Release Notes v0.2.32

Data: 2026-01-06

## Zakres
### Maintenance Events — global endpoints + izolacja tenantów (A5)
Dodano globalne endpointy dla Maintenance Events dopasowane do testu A5:
- MRO tenant z aktywnym dostępem do aircraft i rolą `MRO_EDITOR` może tworzyć Maintenance Event.
- MRO tenant widzi wyłącznie eventy utworzone przez siebie (izolacja po `created_by_tenant_id`).
- Owner tenant widzi wszystkie eventy dla aircraft.
- Tenant bez dostępu do aircraft dostaje odpowiedź `200` z pustą listą (`[]`).

Endpointy (NOWE):
- `POST /v1/maintenance-events`
- `GET /v1/maintenance-events?aircraft_id=...`

Uwagi do payload:
- `event_type` jest zapisywany jako nowa kolumna `event_type` oraz mapowany do istniejącego pola `title` (kompatybilność wstecz).

## Techniczne
- Dodano kolumnę `event_type` do tabeli `public.aircraft_maintenance_events` (idempotentny `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`).
- Dodano nowy moduł API: `modules/maintenance_events`.
- Zaktualizowano `docs/02_api/openapi.yaml` i `docs/00_product/PO_GUIDE.md`.

## Narzędzia uruchomieniowe (Windows)
- Dodano pliki: `start_and_test_v0.2.32.bat`, `start_and_test_DIAG_v0.2.32.bat`.

## v0.2.33

# AviationCAMO-MRO — Release Notes v0.2.34

Date: 2026-01-06

## Fixed
- A5: `GET /v1/maintenance-events?aircraft_id=...` now performs owner check via an explicit query (instead of `db.get()`), improving reliability across environments.
- For MRO tenants with active access, listing returns all events for the aircraft (still access-gated). Tenants without access receive an empty list.

## v0.2.34

# AviationCAMO-MRO v0.2.34 — MAINTENANCE-EVENTS

## Fixes
- Fix: `GET /v1/maintenance-events?aircraft_id=...` now reliably returns events for MRO tenants with active access.
  - Implementation switched to a direct SELECT from `public.aircraft_maintenance_events` to avoid schema/search_path edge cases.
  - Response is always `200` with JSON array (`[]` when empty).

## Behaviour (A5)
- MRO_EDITOR with access can:
  - create maintenance event (POST)
  - list events for the aircraft (GET) and sees the created event
- Tenant without access receives `200` and `[]`.

## v0.2.35

# AviationCAMO-MRO v0.2.35 — MAINTENANCE-EVENTS

## Fixed
- DB sessions are now closed per request.
  - `apps/api/src/shared/db.py:get_db_session` changed from returning a `Session` to a FastAPI generator dependency that `yield`s a session and always calls `db.close()`.
  - This prevents connection leaks that could cause DB endpoints to hang/time out after several calls (seen in A5 `GET /v1/maintenance-events`).

## Notes
- No API contract changes.
- Expected A5 behaviour remains:
  - MRO tenant with active access: can create an event and list returns that event.
  - Tenant without access: list returns `200` and an empty list.

## v0.2.36

# AviationCAMO-MRO v0.2.36 — MAINTENANCE-EVENTS

## Added
- `DELETE /v1/maintenance-events/{event_id}` — usuwa zdarzenie serwisowe w trybie tenant-isolated.
  - Uprawnienia: owner może usuwać zdarzenia dla swoich statków powietrznych; MRO może usuwać własne zdarzenia (`created_by_tenant_id`).
- `DELETE /v1/aircraft/{aircraft_id}/maintenance-events/{event_id}` — usuwa zdarzenie serwisowe w trybie „owner lub przypisane MRO”.
  - Uprawnienia: owner może usuwać dowolne; MRO może usuwać własne.

## Updated
- Zaktualizowano OpenAPI (`docs/02_api/openapi.yaml`) oraz wersję API do `0.2.36`.

## Notes
- Zmiana jest w pełni wstecznie kompatybilna (dodane endpointy).

## v0.2.37

# AviationCAMO-MRO — MAINTENANCE-EVENTS — v0.2.37

## Fixes
- Fixed API startup crash by removing a stray endpoint definition in `apps/api/src/modules/aircraft/router.py` that referenced an undefined `auth` object (previously causing `NameError: name 'auth' is not defined`).

## API / Docs
- OpenAPI spec updated to document tenant-scoped maintenance-event deletion:
  - `DELETE /v1/maintenance-events/{event_id}`

## Legacy (pre-v0.2.28)

## v0.2.35 — Fix: close DB sessions per request (2026-01-06)
### Fixed
- `get_db_session` is now a proper FastAPI generator dependency that always closes the SQLAlchemy session.
- Prevents connection leaks that could cause DB endpoints (including `GET /v1/maintenance-events`) to hang/time out after multiple requests.

## v0.2.34 — Fix: MRO list events returns correct data (A5) (2026-01-06)
### Fixed
- `GET /v1/maintenance-events?aircraft_id=...` now uses a deterministic owner check query (no `db.get()`), addressing cases where MRO list unexpectedly returned an empty result.
- For MRO tenants with active access, listing returns all events for the aircraft (access-gated). Tenants without access still receive an empty list.


## v0.2.32 — Maintenance Events global + tenant isolation (2026-01-06)
### Added
- New global endpoints for Maintenance Events (A5):
  - `POST /v1/maintenance-events`
  - `GET /v1/maintenance-events?aircraft_id=...`

### Changed
- Tenant isolation rules for the new maintenance-events endpoints:
  - Owner sees all events for an aircraft
  - MRO sees events for the aircraft (access-gated)
  - No-access tenant receives `200` + empty list
- DB: added optional column `event_type` to `public.aircraft_maintenance_events`.


## v0.2.31 — Aircraft Maintenance Events (2026-01-06)
### Added
- Aircraft: Maintenance Events (Owner tworzy, MRO czyta i może aktualizować tylko `status` + `mro_notes`)

### Changed
- Docs: zaktualizowano `docs/00_product/PO_GUIDE.md`
- API Spec: zaktualizowano `docs/02_api/openapi.yaml`
- BAT: nowe pliki `start_and_test_v0.2.31.bat`, `start_and_test_DIAG_v0.2.31.bat` + brak natychmiastowego zamykania konsoli


## v0.2.29 — PO Guide + BAT cleanup (2026-01-06)
### Added
- PO-friendly guide: `docs/00_product/PO_GUIDE.md`
- Updated Windows helpers: `start_and_test_v0.2.29.bat`, `start_and_test_DIAG_v0.2.29.bat`

### Changed
- Version bump only (no functional changes vs v0.2.28)

### Removed
- Older `start_and_test*.bat` versions from the ZIP (keep only latest)


## Unreleased
### Added
- (next)

### Changed
- (next)

### Fixed
- (next)

### Security
- (next)


## v0.2.27 (2026-01-06) — Auth/middleware hardening (fix 500 on bad/empty tokens)

### Fixed
- API: invalid/malformed Bearer token now returns **401** instead of **500** (wrap JWKS signing-key resolution errors).
- API: middleware no longer leaks `HTTPException` as `ExceptionGroup` -> **500**; it is translated into a proper JSON response.

### Notes
- Operational change only: no API contract changes for tenants/inventory.
- PowerShell reminder: use the token produced by `scripts\bat\kc_get_token.ps1` (placeholder text in Authorization header will now return 401).

## v0.2.26 (2026-01-05) — KROK 15: First multi-tenant vertical slice (Tenants + Inventory)

### Added
- Core: persistent `public.tenants` table (id, code, name, schema_name, created_at).
- Core: real `/v1/tenants` implementation (GET list, POST create) for `PLATFORM_ADMIN`.
- Multi-tenant bootstrap: on tenant creation the API creates the tenant schema (`tenant_<code>`) and runs minimal migrations (ORM `metadata.create_all`) inside that schema.
- Inventory: new tenant-scoped endpoints `/v1/inventory/parts` (minimal CRUD) backed by tenant schema tables.

### Changed
- Tenant context: schema is resolved from `public.tenants.schema_name` when available; fallback remains deterministic UUID-based schema (`t_<uuid_without_dashes>`).
- API version bumped to `0.2.26`.
- OpenAPI contract updated (tenant fields: code + schema_name; added Inventory tag and `/v1/inventory/parts`).

### Notes
- Tenant header/token contract remains `X-Tenant-Id` = tenant UUID.
- For smoke test C), use the tenant UUID returned from POST `/v1/tenants` as `X-Tenant-Id` for Inventory calls.


## v0.2.25 (2026-01-05) — BAT DIAG polish fixes (KROK 14D)
### Fixed
- DIAG port checks now report correctly (store connection state before closing the TCP client).
- Removed escaped quotes in "Log saved to" path output on Windows.

### Changed
- Increased DIAG port-check connect timeout to 1500ms for stability on busy machines.


## v0.2.9 (2026-01-05) — BAT logging + Docker Engine retry (KROK 14B)
### Added
- Batch script now writes a timestamped run log to `.\logs\start_and_test_v0.2.9_YYYYMMDD_HHMMSS.log`.

### Changed
- Prerequisite check for Docker Engine now waits/retries before failing (10 attempts x 5s).

### Fixed
- Defensive cleanup against a stray standalone `\` line in the batch file that can trigger: `'\' is not recognized as an internal or external command`.
- Improved error logging: key docker-compose / curl steps append stderr to the run log.

## v0.2.6 (2026-01-05) — Fix JWT audience handling + return 401 instead of 500
### Added
- Clear auth error handling (AuthError) mapped to HTTP 401

### Changed
- Audience (`aud`) is validated ONLY if `OIDC_AUDIENCE` is explicitly set
- Dev docker-compose no longer sets `OIDC_AUDIENCE` by default

### Fixed
- 500 error on `/v1/tenants`: `MissingRequiredClaimError: Token is missing the "aud" claim`

## v0.2.5 (2026-01-05) — Dev issuer/JWKS alignment (Keycloak via localhost)
### Added
- `OIDC_JWKS_URL` override for JWKS fetch (supports `host.docker.internal`)

### Changed
- Dev `OIDC_ISSUER` set to `http://localhost:8080/realms/aviation` to match tokens obtained from host port-mapping

### Fixed
- 500 error on `/v1/tenants` caused by issuer mismatch (`localhost` vs `keycloak`) in JWT verification

### Security
- JWT verification remains enabled; this change only aligns dev endpoints.

## v0.2.4 (2026-01-05) — JWT verification (JWKS) + RBAC minimum
### Added
- JWT signature verification against Keycloak JWKS (RS256)
- Optional audience validation via `OIDC_AUDIENCE`
- RBAC enforcement helper + protected `/v1/tenants` endpoint (Platform Admin)
- Debug tenant header disabled by default (`DEBUG_TENANT_HEADER=false`)

### Changed
- OIDC issuer in docker-compose set to realm `aviation`

### Fixed
- Reduced risk: debug tenant injection is now opt-in (dev only)

### Security
- `/v1/*` endpoints require bearer token (except `/health`)

## v0.2.3 (2026-01-05) — Fix API DB driver (psycopg2)
### Added
- psycopg2-binary dependency for SQLAlchemy default PostgreSQL dialect

### Changed
- N/A

### Fixed
- API container crash: ModuleNotFoundError: psycopg2

### Security
- N/A

## v0.2.2 (2026-01-05) — Tenant context plumbing (schema routing)
### Added
- Tenant context middleware (token decode plumbing + headers)
- Schema-per-tenant routing via PostgreSQL search_path (contextvars + SQLAlchemy checkout hook)
- Debug endpoint: `/v1/_debug/context`
- API docs updated with tenant resolution rules

### Changed
- API runtime version bumped to 0.2.2
- OpenAPI contract updated to 0.2.2 (includes debug endpoint)

### Fixed
- N/A

### Security
- Token verification not enforced yet (plumbing only); production step will add JWKS verification.

## v0.2.1 (2026-01-05) — Runtime baseline (Docker Compose)
### Added
- Keycloak realm import (infra/docker/keycloak/realm-aviation.json) + compose import-realm
- API container serves OpenAPI from docs/02_api/openapi.yaml via `/docs` and `/openapi.json`
- Worker container stable entrypoint (placeholder loop)
- Dev smoke test script: scripts/dev/smoke_test.sh

### Changed
- Fixed Dockerfile paths for monorepo runtime

### Fixed
- API Docker entrypoint now runs `uvicorn main:app`

### Security
- OIDC bearer scheme kept in OpenAPI; token validation wired in future step (post-plumbing)

## v0.2.0 (2026-01-05) — API Contract baseline
### Added
- OpenAPI v0.2.0: Core + CAMO + MRO + Logistics + Integrations endpoints (contract only)
- Tenant context rules in API docs (`docs/02_api/README.md`)
- Master doc reference to API contract

### Changed
- N/A

### Fixed
- N/A

### Security
- Defined OIDC/JWT bearer scheme in OpenAPI

## v0.1.0 (2026-01-05) — Foundation skeleton
### Added
- Monorepo structure: web / api / worker / infra / db / docs
- Master documentation baseline (Vision, Decisions, WBS, RBAC, Architecture)
- Docker Compose skeleton: api, worker, postgres, redis, keycloak
- API skeleton with `/health` endpoint
- Worker skeleton (Celery) with placeholder task module

### Changed
- N/A

### Fixed
- N/A

### Security
- RBAC and auditability principles documented for MVP baseline
## v0.2.8 (2026-01-05)

- Inventory/Logistics skeleton (models + minimal CRUD + bootstrap + SQL migration refs)
- Added start_and_test_v0.2.8.bat (includes Logistics bootstrap call)
- Based on latest repo snapshot provided (Aviation-CAMO-MRO-system-main.zip)

## v0.2.7 — Inventory/Logistics skeleton (KROK 14)
Date: 2026-01-05

### Added
- Logistics module: SQLAlchemy ORM models for Part, Warehouse, Location, StockItem + shared UoM dictionary.
- CRUD endpoints (minimal): /v1/logistics/parts, /warehouses, /locations, /stock-items, /uom.
- Dev bootstrap endpoint: POST /v1/logistics/_admin/bootstrap (creates schemas/tables + seeds UoM).
- Tenant schema auto-create: middleware ensures tenant schema exists (CREATE SCHEMA IF NOT EXISTS).

### Docs
- Added high-level WBS: docs/01_architecture/wbs_modules.md
- Updated architecture overview to reference WBS.

### Notes
- This version uses ORM `metadata.create_all` as a temporary migration mechanism.
- SQL reference migrations added under db/migrations (shared + tenant) for future hardening.

## v0.2.19 (2026-01-05)
- KROK 14C: stable Windows BAT hardening + diagnostics.
- Added /diag mode, exit codes, and SUMMARY section.
- Added PowerShell scripts for HTTP checks, token acquisition, and Bearer calls.
- Added concurrency guard to prevent parallel runs.

## v0.2.21 - 2026-01-05
- KROK 14C: rebuilt Windows BAT runner with deterministic stop-on-fail and a single SUMMARY.
- Rewrote scripts/bat/*.ps1 (health/well-known wait, token, bearer call, DIAG helpers) to eliminate corrupted lines and improve reliability.
- Added concurrency lock to prevent parallel runs.

## v0.2.24 - 2026-01-05
### Changed
- BAT logger uses safe `echo(`-style output to avoid `ECHO is off.` noise in console/logs.
- DIAG now runs via `scripts/bat/run_diag.ps1` and writes diagnostic command output to both console and log file (docker version/info, compose ps, port checks).
## v0.2.43 (2026-01-07)

### Added
- **UI v1**: lekki frontend „produktowy” (CAMO / MRO) działający pod `http://localhost:3000` (bez logowania).
- **Aircraft (lista)**: czytelny widok tabelaryczny danych z API (`GET /v1/aircraft`).
- **Maintenance Events (lista)**: czytelny widok tabelaryczny danych z API (`GET /v1/maintenance-events`) w kontekście CAMO i MRO.
- UI pobiera dane **wyłącznie** z REST API (brak omijania backendu).

## v0.2.44
- UI: Keycloak login (OIDC code + PKCE) + logout.
- UI: role-based navigation (CAMO vs MRO) based on Keycloak realm roles.
- API: RBAC enforced for /v1/aircraft (CAMO roles) and /v1/maintenance-events (CAMO or MRO roles).
- Keycloak: added test users camo_user (CAMO_PLANNER) and mro_user (MECHANIC).

## v0.2.45 (2026-01-07)

### Added
- **OPS documentation**: production server SSH-only access, sshd hardening and deployment contract (`docs/03_ops/SERVER_AND_DEPLOYMENT.md`).
- **PO documentation**: infrastructure & deployment summary (`docs/00_product/PO_PROD_WORKFLOW.md`).

### Security
- Documented the enforced policy: **no password SSH**, **root key-only**.

## v0.2.3.2 (2026-01-09)
- DB Import: added server-compatible import SQL (Hetzner/prod schema) and verification script.
- Docs: extended DB import documentation with server deployment path and schema mapping (no history removal).

## v0.2.4 — SERVER RBAC SYNC

### Database
- Applied RBAC schema migration (public.auth_*) on SERVER.
- Seeded RBAC catalog v0.2.4 (roles, permissions, mappings).
- Server DB aligned with LOCAL after AUTH/RBAC freeze.

### API validation
- /v1/tenants: no token → 401
- /v1/tenants: PLATFORM_ADMIN → 200 OK
- API logs: no DB relation errors (UndefinedTable / relation does not exist / permission denied)



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## 2026-01-11 (ops) — EPIC0B B1 tenant routing E2E

- Verified schema-per-tenant routing in API (tenant schema resolved at request-time).
- Added controlled debug routing via `X-Debug-Tenant-Id` gated by `DEBUG_TENANT_HEADER`.
- UI bootstrap: OIDC code+PKCE against Keycloak (public client `aviation-ui`) + stable `API Base URL` persistence.
- Public HTTPS entrypoints validated: `app.*` (UI), `api.*` (API), `auth.*` (Keycloak).

## 2026-01-11 — EPIC0B B1 schema-per-tenant routing (E2E-ready)

### Added / Changed
- **Tenant routing middleware** (API): resolves tenant schema per request.
- **Tenant resolution order** (documented + verified in E2E):
  1. `X-Tenant-Id` header **only** for `PLATFORM_ADMIN` (admin override)
  2. `tenant_id` claim from access token (target PROD path)
  3. `X-Debug-Tenant-Id` header when `DEBUG_TENANT_HEADER=true` (E2E bootstrap / non-prod)
- **Diagnostics**: API returns `X-Tenant-Id`, `X-Tenant-Schema`, `X-Tenant-Source` response headers for troubleshooting.
- **Public HTTPS**: reverse proxy routing for `app.*`, `api.*`, `auth.*` (Caddy) with CORS validated for `app.* → api.*`.
- **UI (static)**: OIDC Authorization Code + PKCE wiring aligned to Keycloak; debug-tenant header usage for E2E.

### Notes / Risks
- `DEBUG_TENANT_HEADER` MUST remain **false** by default and must not be enabled permanently in PROD.
- Long-term: UI should stop using debug header and rely on `tenant_id` claim from token.
