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
