# Architecture Overview (High-Level)

## Runtime Components
- Web UI (React/TypeScript)
- API (FastAPI)
- Worker (Celery)
- PostgreSQL (schema-per-tenant)
- Redis (queue)
- Keycloak (OIDC)

## Principles
- Tenant isolation via PostgreSQL schemas
- Auditability by design (immutable audit events)
- Integration layer with retry + idempotency


## Modules (WBS)
See: `docs/01_architecture/wbs_modules.md`.
