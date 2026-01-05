# Release Notes

## v0.2.11 (2026-01-05)
- FIX: BAT – token handling hardened (trim) to prevent missing/invalid Authorization header on Windows.
- FIX: /v1/tenants call now passes token via env var (avoids cmd quoting edge-cases) and uses PowerShell ErrorAction Stop.
- KEEP: diagnostics mode, unified exit codes, SUMMARY section, logs to .\logs.


## Unreleased
### Added
- (next)

### Changed
- (next)

### Fixed
- (next)

### Security
- (next)









## v0.2.10 (2026-01-05)
### Added
- Windows BAT: diagnostics mode (DIAG=1 or /diag + dedicated start_and_test_DIAG_v0.2.10.bat) capturing: docker version/info (selected), docker compose version, docker compose ps, and port checks for 8000/8080.
- Log footer SUMMARY section (OK/FAIL + cause + exit code + log file path) for self-service troubleshooting.

### Changed
- Windows BAT: standardized failure exit codes for common failure points (Docker Engine, compose build/up, API health, Keycloak well-known, token, /v1/tenants).

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

## v0.2.12 — BAT PS1 stability for tenants/bootstrap
- Fix: replace inline PowerShell blocks with dedicated scripts (call_tenants.ps1, call_bootstrap.ps1) to avoid parser/quoting issues on Windows.
- Keep: DIAG mode, SUMMARY, exit codes, logs in .\logs, pause, start_and_test flow.
