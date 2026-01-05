# API Contract (OpenAPI)

File: `openapi.yaml`

## Auth (v0.2.4)
- Bearer JWT tokens are verified against Keycloak JWKS (RS256) when `OIDC_ISSUER` is set.
- Roles are extracted from Keycloak realm roles (`realm_access.roles`).

### Runtime env
- `OIDC_ISSUER`: e.g. `http://keycloak:8080/realms/aviation`
- `OIDC_AUDIENCE`: `aviation-api` (optional, enforced if set)
- `DEBUG_TENANT_HEADER`: `false` by default

## Tenant Context Rules (v0.2.4)
1. `X-Tenant-Id` allowed ONLY for `PLATFORM_ADMIN` (cross-tenant).
2. Otherwise tenant is resolved from verified token claim `tenant_id`.
3. `X-Debug-Tenant-Id` is available ONLY if `DEBUG_TENANT_HEADER=true`.

## Debug endpoint
- `GET /v1/_debug/context` exists only when `DEBUG_TENANT_HEADER=true`.

## Dev issuer/JWKS note (Windows Docker Desktop)
If you obtain tokens from `http://localhost:8080`, Keycloak sets `iss` to `http://localhost:8080/...`.
API container verifies `iss` against `OIDC_ISSUER` and fetches JWKS via `OIDC_JWKS_URL` (use `host.docker.internal`).
