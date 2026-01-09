# RBAC Matrix — MVP Baseline


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

## Permission Groups
- CORE: manage_tenants, manage_users, manage_roles, view_audit, view_reports
- CAMO: view_aircraft, edit_aircraft, manage_program, manage_due, manage_defects
- MRO: manage_workorders, manage_tasks, sign_off
- LOGISTICS: manage_parts, manage_inventory, manage_movements, manage_costs
- INTEGRATION: view_integrations, retry_integrations

## Role → Permissions (MVP)
- Platform Admin: CORE(all) + INTEGRATION(all)
- Tenant Admin: CORE(manage_users, manage_roles, view_audit, view_reports) + INTEGRATION(view_integrations)
- Auditor: CORE(view_audit, view_reports) + CAMO(view*) + MRO(view*) + LOGISTICS(view*)
- CAMO Planner: CAMO(view_aircraft, manage_program, manage_due, manage_defects)
- CAMO Engineer: CAMO(view_aircraft, edit_aircraft, manage_defects) + LOGISTICS(view_inventory)
- Maintenance Planner: MRO(manage_workorders, manage_tasks) + LOGISTICS(view_inventory)
- Mechanic: MRO(manage_tasks) + LOGISTICS(manage_movements)
- Certifying Staff: MRO(sign_off) + MRO(view*)
- Logistics Officer: LOGISTICS(all) + CORE(view_reports)
- Finance / Cost Controller: LOGISTICS(manage_costs, view_inventory) + CORE(view_reports)

## Notes
- Ten dokument to baseline produktowy (MVP). Implementacja w DB: `db/migrations/public/0003_public_auth_rbac.sql`
- Seed katalogu ról/uprawnień: `db/seed/seed_public_auth_rbac_catalog_v0.2.4.sql`
