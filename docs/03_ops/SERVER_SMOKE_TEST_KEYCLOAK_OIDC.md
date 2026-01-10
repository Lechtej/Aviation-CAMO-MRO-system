# Server Smoke Test – Keycloak / OIDC (client_credentials)


## STATUS FREEZE (2026-01-09) – Local dev closure (Keycloak + API + RBAC DB)

### What was fixed
- API `GET /v1/tenants` was failing with **500** due to missing RBAC tables: `public.auth_permissions` (and related).
- Applied DB migration + seeds:
  - `db/migrations/public/0003_public_auth_rbac.sql`
  - `db/seed/seed_public_auth_rbac_catalog_v0.2.4.sql`
  - `db/seed/seed_public_auth_rbac_kc_bridge_v0.2.4.sql`

### Verified outcomes (evidence)
- API: `GET http://localhost:8000/health` → **200** `{"status":"ok"}`
- Token issuance (example users):
  - `test_platform_admin` → role includes `PLATFORM_ADMIN`
  - `test_auditor` → role includes `AUDITOR`
- API call with bearer token:
  - `GET http://localhost:8000/v1/tenants` → **200** `[]`
- DB RBAC objects exist and are populated:
  - tables: `public.auth_roles`, `public.auth_permissions`, `public.auth_role_permissions`
  - counts: roles **68**, permissions **71**, mappings **619**

### PowerShell helpers (recommended)
```powershell
function Get-KcToken {
  param(
    [string]$KC = "http://localhost:8080",
    [string]$Realm = "aviation",
    [string]$ClientId = "aviation-api",
    [string]$User,
    [string]$Pass
  )

  $resp = curl.exe -s -X POST "$KC/realms/$Realm/protocol/openid-connect/token" `
    -H "Content-Type: application/x-www-form-urlencoded" `
    -d "grant_type=password" `
    -d "client_id=$ClientId" `
    -d "username=$User" `
    -d "password=$Pass"

  $tok = ($resp | ConvertFrom-Json).access_token
  if (-not $tok -or $tok.Length -eq 0) { throw "TOKEN_EMPTY" }
  return $tok
}

$TOKEN = Get-KcToken -User "test_auditor" -Pass "Test1234!"
curl.exe -i -s --max-time 10 "http://localhost:8000/v1/tenants" -H "Authorization: Bearer $TOKEN"
```

### Common pitfall
- Running commands from `C:\WINDOWS\system32` breaks relative paths (e.g., compose file). Always `cd` to repo root before `docker compose ...`.

## Scope
Server-side smoke test for AviationCAMO-MRO-system:
- Keycloak OIDC
- client_credentials
- PLATFORM_ADMIN
- Tenant bootstrap
- Logistics & Inventory happy-path

---

## Preconditions
- Docker + docker-compose
- keycloak / api / postgres containers running

---

## Token
Use client_credentials.
Regenerate often (short TTL).

---

## Tenant
Create tenant via /v1/tenants.
All tenant endpoints require X-Tenant-Id header.

---

## Logistics bootstrap
POST /v1/logistics/_admin/bootstrap

---

## Happy-path
- inventory part
- warehouse
- location
- stock-item

---

## Known issue
POST /v1/logistics/movements → 404 Not Found


## STATUS FREEZE (2026-01-10) — UI over HTTPS (OIDC code+PKCE) + API calls (read-only)

### Endpoints (prod)
- UI: https://app.forgemotionsystems.com
- API: https://api.forgemotionsystems.com
- Keycloak: https://auth.forgemotionsystems.com
- OIDC issuer: https://auth.forgemotionsystems.com/realms/aviation

### UI auth flow (SPA)
- Protocol: Authorization Code + PKCE (S256)
- Token storage: `localStorage["aviationcamo_auth_v1"]`
- Expected redirect_uri: `https://app.forgemotionsystems.com/`

### Keycloak client settings (minimum)
Client: `aviation-api` (realm: `aviation`)
- Valid Redirect URIs:
  - `https://app.forgemotionsystems.com/`
  - `https://app.forgemotionsystems.com/*`
- Web Origins:
  - `https://app.forgemotionsystems.com`

### Production CORS requirement (browser)
API must allow origin:
- `https://app.forgemotionsystems.com`

Note:
- verify with preflight (OPTIONS) against `/v1/aircraft` using that origin.

### Tenant context requirement (current)
Tenant-scoped endpoints (e.g. `/v1/aircraft`) require tenant context to be resolved.
Resolution rules are documented in:
- `docs/02_api/TENANT_CONTEXT.md`

### Smoke-test checklist (PASS/FAIL)
1) UI secure context:
   - `window.isSecureContext === true` (browser console)
2) PKCE availability:
   - `crypto.subtle.digest` exists
3) Login redirect:
   - host `auth.forgemotionsystems.com`
   - `code_challenge_method=S256`
4) After login:
   - `localStorage["aviationcamo_auth_v1"].access_token` exists
5) API connectivity:
   - `GET /docs` → 200 (UI shows API OK)
6) Auth:
   - `GET /v1/roles` with Bearer → 200
7) Tenant:
   - `GET /v1/aircraft`:
     - without tenant context → may be 403
     - with tenant context (claim or `X-Tenant-Id`) → 200

