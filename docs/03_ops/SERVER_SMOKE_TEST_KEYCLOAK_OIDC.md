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
