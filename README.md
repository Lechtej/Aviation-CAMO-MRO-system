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
