# API Contract (OpenAPI)

File: `openapi.yaml`

## Auth (v0.2.4)
- Bearer JWT tokens are verified against Keycloak JWKS (RS256) when `OIDC_ISSUER` is set.
- Roles are extracted from Keycloak realm roles (`realm_access.roles`).

### Token lifetime
- In the default dev realm config, `access_token` is short-lived (typically **300s**).
- If you see `Invalid token: Signature has expired`, obtain a fresh token and retry.

### Docker networking: issuer vs JWKS
Depending on where you obtain the token from, your JWT `iss` claim will differ:

- **Token acquired from inside Docker network** (calling Keycloak via service name `keycloak:8080`) → `iss = http://keycloak:8080/realms/aviation`
- **Token acquired from the host** (calling Keycloak via port-mapping on the host, e.g. `127.0.0.1:8080`) → `iss = http://127.0.0.1:8080/realms/aviation`

The API checks that `iss` matches `OIDC_ISSUER`, and fetches JWKS from `OIDC_JWKS_URL`.

Recommended server/dev defaults:

- `OIDC_ISSUER=http://127.0.0.1:8080/realms/aviation` (matches tokens obtained from the host)
- `OIDC_JWKS_URL=http://keycloak:8080/realms/aviation/protocol/openid-connect/certs` (reachable from the API container)

See also: `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md`.

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

## Import-time stability (SQLAlchemy models)

- Validate runtime imports inside container:

```bash
cd infra/docker
docker compose run --rm api bash -lc 'python -c "import modules.logistics.models; print(\\"OK: logistics models imported\\")"'
docker compose run --rm api bash -lc 'python -c "import main; print(\\"OK: main imported\\")"'
```



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

## EPIC1 — Work Orders (design-only) [2026-01-11]
- Contract: `work_orders_contract.md`

## Logistics API (Parts/Stock) — MVP

**Update 2026-01-12**

### Logistics (MVP) — endpoints

Tenant-scoped prefix: `/v1/logistics/*` (requires header `X-Tenant-Id: <tenant_uuid>`).

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /v1/logistics/uom` | list shared UoM dictionary | read-only |
| `GET/POST/PUT/DELETE /v1/logistics/parts` | Parts master data | `part_number` unique |
| `GET/POST/PUT/DELETE /v1/logistics/warehouses` | Warehouse dictionary | `code` unique |
| `GET/POST/PUT/DELETE /v1/logistics/locations` | Locations under warehouse | `(warehouse_id, code)` unique |
| `GET/POST/PUT/DELETE /v1/logistics/stock-items` | Stock items per (part, location, serial) | tenant data |
| `POST /v1/logistics/stock-transactions` | Apply stock delta (RECEIPT/ISSUE/RETURN) | **No RBAC yet** (planned) |

### `POST /v1/logistics/stock-transactions`

Request (JSON):
- `type`: `RECEIPT` \| `ISSUE` \| `RETURN`
- `stock_item_id`: UUID
- `qty`: number > 0

Response (JSON):
- `transaction_id`: UUID (temporary; not persisted yet)
- `stock_item_id`: UUID
- `qty_on_hand`: number

Failure modes:
- `401` — missing/invalid bearer token
- `400/500` — invalid `X-Tenant-Id` header (must be UUID of an existing tenant); see `TENANT_CONTEXT.md`
- `404` — `stock_item_id` not found
- `409` — `ISSUE` exceeds `qty_on_hand`
- `422` — invalid `type`

Implementation note:
- qty is casted via `Decimal(str(payload.qty))` to avoid float rounding.
