# Aviation CAMO & MRO Platform (Foundation)

**Version:** v0.1.0 (Foundation skeleton)

This repository is a *foundation skeleton* for a multi-tenant CAMO + MRO + Logistics SaaS platform.
No business logic is implemented yet; the goal is to provide structure, documentation, and a runnable scaffold.

## Quick start (local, Docker)
1. Install Docker Desktop
2. From repository root:
   - `docker compose -f infra/docker/docker-compose.yml up --build`

Services:
- `api` (FastAPI skeleton, health endpoint)
- `worker` (Celery skeleton)
- `db` (PostgreSQL)
- `redis`
- `keycloak` (OIDC) – for now: placeholder config

## Docs
- Master document: `docs/master/AVIATION_CAMO_MRO_MASTER_DOC.md`
- WBS / RBAC / ERD: `docs/00_product/`
- API contract: `docs/02_api/openapi.yaml`


## Runtime verification (KROK 11A)
1. `docker compose -f infra/docker/docker-compose.yml up --build`
2. Check:
   - API health: `http://localhost:8000/health`
   - API docs: `http://localhost:8000/docs`
   - Keycloak: `http://localhost:8080` (Realm: `aviation`)
3. Test users (dev only):
   - platformadmin / platformadmin
   - tenantadmin / tenantadmin
