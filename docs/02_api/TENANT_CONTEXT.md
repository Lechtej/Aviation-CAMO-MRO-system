# API — Tenant Context (multi-tenant schema-per-tenant)

## Scope
This document defines **how the API resolves tenant context** for tenant-scoped endpoints (e.g. `/v1/aircraft`, `/v1/maintenance-events`)
and how UI/tools must provide tenant information.

## Facts (current implementation)
Tenant context is resolved in API middleware (`apps/api/src/main.py`).

Resolution order:

1. **Header `X-Tenant-Id`** — accepted only when the authenticated user has `PLATFORM_ADMIN` role  
   - source: `"header(platform_admin)"`
2. **JWT claim `tenant_id`** — if present in verified token claims  
   - source: `"token(tenant_id)"`
3. **Debug header `X-Debug-Tenant-Id`** — only when `DEBUG_TENANT_HEADER=true`  
   - source: `"header(debug)"`

If none of the above provides a tenant id:
- schema defaults to `public`
- tenant-scoped endpoints may return **403** (role/tenant required)

## Header contract

### X-Tenant-Id
- Type: UUID string
- Example: `X-Tenant-Id: 3f0b0b9e-....-....`

### Response headers (when tenant resolved)
API adds:
- `X-Tenant-Id`
- `X-Tenant-Schema`
- `X-Tenant-Source`

These are useful for debugging whether schema switching is active.

## Quick tests

### 1) Verify token roles
In browser / tooling:
- `GET https://api.forgemotionsystems.com/v1/roles` with Bearer → expect `200`

### 2) List tenants (public list is allowed for authenticated users)
- `GET https://api.forgemotionsystems.com/v1/tenants` with Bearer → expect `200` + list

### 3) Tenant-scoped endpoint with explicit tenant header (admin path)
Replace `<TENANT_UUID>` with a real tenant id from `/v1/tenants`:

```bash
curl -i "https://api.forgemotionsystems.com/v1/aircraft" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "X-Tenant-Id: <TENANT_UUID>"
```

PASS indicators:
- HTTP `200`
- response contains `X-Tenant-Id` / `X-Tenant-Schema`

## Implementation note (decision point)
There are two supported product models:

### Model A (recommended for prod): tenant_id in JWT
- Keycloak provides `tenant_id` claim in access token.
- API resolves tenant automatically; UI does not send tenant headers.
- Requires Keycloak mapper + tenant assignment process.

### Model B (admin tooling): X-Tenant-Id header
- UI/admin tools explicitly pick tenant and send `X-Tenant-Id`.
- API accepts it only for `PLATFORM_ADMIN`.
- Recommended for admin console / support tooling and debugging.

Pick one as the **primary** approach for UI (do not mix in the long term).



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-11 — Practical E2E routing rules (as implemented)

### Resolution order (effective)
1. **Admin override**: `X-Tenant-Id` header **only** when caller has `PLATFORM_ADMIN`.
2. **Token claim**: `tenant_id` from access token (target state for PROD).
3. **Debug override**: `X-Debug-Tenant-Id` **only** when `DEBUG_TENANT_HEADER=true` (E2E bootstrap / non-prod).

### Recommended usage
- **PROD**: require `tenant_id` in access token; keep `DEBUG_TENANT_HEADER=false`.
- **E2E / bootstrap**: temporarily enable `DEBUG_TENANT_HEADER=true` and call API with `X-Debug-Tenant-Id`.

### Minimal curl template
```bash
curl -sS -i   -H "Authorization: Bearer $TOKEN"   -H "X-Debug-Tenant-Id: <TENANT_UUID>"   https://api.forgemotionsystems.com/v1/aircraft
```
Expected response headers (example):
- `x-tenant-id: <TENANT_UUID>`
- `x-tenant-schema: t_<schema>`
- `x-tenant-source: header(debug)`

## ADDENDUM 2026-01-11 — Verified E2E tenant routing & debug bootstrap

### What was verified
- Request routing to tenant schema works end-to-end (Keycloak → API → DB schema), confirmed by:
  - `X-Tenant-Schema` response header (e.g. `t_aca`).
  - Successful data reads (e.g. `GET /v1/aircraft`) when tenant context is resolved.

### Recommended defaults
- **PROD target:** rely on `tenant_id` claim in the access token.
- **E2E bootstrap:** allow `X-Debug-Tenant-Id` only when `DEBUG_TENANT_HEADER=true` (explicitly enabled).

### Minimal curl checks
```bash
# obtain access token (example)
ISS="https://auth.forgemotionsystems.com/realms/aviation"
TOK="$ISS/protocol/openid-connect/token"

RESP_JSON="$(curl -sS -X POST "$TOK" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "client_id=aviation-api" \
  --data-urlencode "username=camo_user" \
  --data-urlencode "password=***")"

TOKEN="$(printf '%s' "$RESP_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')"

# debug tenant header (only if DEBUG_TENANT_HEADER=true)
curl -sS -i \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Debug-Tenant-Id: <TENANT_UUID>" \
  https://api.forgemotionsystems.com/v1/aircraft | head -n 40
```

### Security note
- `X-Debug-Tenant-Id` is a **temporary escape hatch**. Keep it disabled by default and remove it from UI once `tenant_id` claim is provided by the auth layer.

## ADDENDUM 2026-01-11 — debug header + E2E curl (B1 verification)

### Szybki test routingu (curl)

1) Pobierz token (przykład: password grant dla test-user):

```bash
set +H
ISS="https://auth.forgemotionsystems.com/realms/aviation"
TOK="$ISS/protocol/openid-connect/token"

CLIENT_ID="aviation-api"
USER="camo_user"
PASS='qwe123!@#'

RESP_JSON="$(curl -sS -X POST "$TOK"   -H "Content-Type: application/x-www-form-urlencoded"   --data-urlencode "grant_type=password"   --data-urlencode "client_id=$CLIENT_ID"   --data-urlencode "username=$USER"   --data-urlencode "password=$PASS")"

TOKEN="$(printf '%s' "$RESP_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')"
```

2) Wywołaj API z tenant context:

- **DEV/DEMO:** `X-Debug-Tenant-Id` (wymaga `DEBUG_TENANT_HEADER=true` w API env)

```bash
curl -sS -i   -H "Authorization: Bearer $TOKEN"   -H "X-Debug-Tenant-Id: <TENANT_UUID>"   https://api.forgemotionsystems.com/v1/aircraft | head -n 40
```

- **PROD docelowo:** `tenant_id` w claim tokena (bez debug header).

### Oczekiwane response headers

- `x-tenant-id`: tenant UUID
- `x-tenant-schema`: np. `t_aca`
- `x-tenant-source`: np. `token(claim)` / `header(debug)` / `header(platform_admin)`

### Konsekwencja bezpieczeństwa

`X-Debug-Tenant-Id` to mechanizm operacyjny. Musi być:
- jawnie włączany env (`DEBUG_TENANT_HEADER=true`) wyłącznie na dev/demo,
- domyślnie wyłączony na prod.

## ADDENDUM 2026-01-11 - Tenant resolution + debug header

### Aktualny kontrakt (po wdrozeniu EPIC0B B1)

Kolejnosc ustalania *tenant context* (routing do schemy t_<tenant_code>):

1. **Header `X-Tenant-Id`** *(tylko PLATFORM_ADMIN)*
   * Wymaga zalogowania (bearer JWT) oraz roli uprawnionej do cross-tenant.
   * Zastosowanie: operacje administracyjne / serwisowe.

2. **Claim `tenant_id` w JWT** *(tryb docelowy / produkcyjny)*
   * Wymaga mapowania atrybutu uzytkownika w Keycloak do claimu `tenant_id`.

3. **Header `X-Debug-Tenant-Id`** *(tylko gdy `DEBUG_TENANT_HEADER=true` w API)*
   * Zastosowanie: E2E/dev/demo, gdy nie mamy jeszcze claimu `tenant_id`.
   * Ryzyko: potencjalny bypass izolacji tenantow - **w prod MUST BE OFF**.

### Jak rozpoznac, ze routing zadzialal

Kazda odpowiedz API powinna zwracac naglowki diagnostyczne (pomocne w testach):

* `x-tenant-id`
* `x-tenant-schema`
* `x-tenant-source` (np. `token.claim(tenant_id)` / `header(platform_admin)` / `header(debug)`)

### Minimalny test (curl)

*Uwaga:* ponizszy przyklad zaklada, ze API ma wlaczony debug header.

```bash
curl -i   -H "Authorization: Bearer <JWT>"   -H "X-Debug-Tenant-Id: <TENANT_UUID>"   https://api.forgemotionsystems.com/v1/aircraft
```
