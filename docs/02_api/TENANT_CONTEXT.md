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

