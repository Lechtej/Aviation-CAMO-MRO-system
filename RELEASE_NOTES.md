# Release Notes

## Unreleased
### Added
- (next)

### Changed
- (next)

### Fixed
- (next)

### Security
- (next)



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
