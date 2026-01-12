# Deployment (MVP)

Ten dokument jest **skrótowym stubem**. Docelowy opis produkcji i dostępu do serwera znajduje się tutaj:
- `docs/03_ops/SERVER_AND_DEPLOYMENT.md`

## Local
Use Docker Compose under `infra/docker/docker-compose.yml`.

## Environments
- dev (local)
- staging (overlay: `infra/staging/docker-compose.staging.yml`)
- prod (post-MVP)

## Notes
- Kubernetes support can be added post-MVP.

## DEV runtime: API code sync (Docker COPY vs bind-mount)

### Problem
The `api` container ships application code into the image during build (see `infra/docker/api.Dockerfile`).
Runtime code lives under `/app` inside the container.

### Consequence (DEV)
Host-side changes in `apps/api/src/...` are NOT visible in the running container unless the image is rebuilt.

### Required workflow for backend code changes (DEV)
From `infra/docker`:

```bash
docker compose build --no-cache api
docker compose up -d api
docker compose logs -n 80 --no-color api
```

PASS: container starts cleanly and subsequent curl tests hit the updated behavior.

### Recommendation (post #10.1): dev-only bind-mount (mini-task)
To avoid rebuilds for every small change in DEV, add a DEV-only bind-mount so that `apps/api/src` is mounted into `/app`.

Rules:
- DEV-only (never in production compose)
- implemented as an override file (e.g. `docker-compose.dev.yml`) or compose profile

See: `docs/03_ops/DEV_DOCKER_BIND_MOUNT_MINI_TASK.md`.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

## Keycloak: password grant unblocker for test environment

If your UI/API tests rely on `grant_type=password` and you get:
- `invalid_grant` / `Account is not fully set up`

Use the documented workaround:
- `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md` → **Fix: invalid_grant / Account is not fully set up**
