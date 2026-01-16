# AviationCAMO-MRO-system_DB — Release Notes (cumulative)

## v0.2.2 (2026-01-08)

### Added
- Public schema migrations:
  - tenant groups (PGL)
  - tenants with tenant_type (MRO/CAMO/AIRLINE_CUSTOMER)
  - mro↔customer relations
  - global aircraft registry + MRO access + maintenance events
- Seed script:
  - PGL tenants: LOTAMS, LST, LOT (CAMO)
  - customer airlines list imported from `Floty_MRO_PGL_v1.1.1.xlsx` (sheet `Airlines`)
  - LOT fleet imported from sheet `Fleet_SAMPLE` and shared as public aircraft

## v0.2.3 (2026-01-09)

### Added
- PGL import tooling under `db/import/`:
  - XLSX source (`db/import/source/Floty_MRO_PGL_v1.1.1_FINAL.xlsx`)
  - XLSX→CSV exporter (`scripts/xlsx_to_csv.py`, `db/import/scripts/import_pgl_fleet.py`)
  - Staging loader SQL (`db/import/staging/load_from_csv.sql`)
  - Verification SQL (`db/import/scripts/verify_import.sql`)

### Notes
- Real-world dataset may contain duplicate MSN values while `public.aircraft` enforces unique non-null MSN (`ux_aircraft_msn_not_null`).
- Validated import uses `aircraft_dedup.csv` (929→928) and yields:
  - `public.aircraft` = 928
  - `public.aircraft_mro_access` = 928
  - `orphan_access` = 0

## v0.2.4 — RBAC Catalog (roles + permissions)

- DB: added RBAC catalog tables in `public` schema:
  - `auth_roles`, `auth_permissions`, `auth_role_permissions`
- DB Seed: added `seed_public_auth_rbac_catalog_v0.2.4.sql` (idempotent)
- Docs: updated RBAC matrix with DB-backed catalog contract (Keycloak role codes must match DB `auth_roles.code`)

## v0.2.4 — RBAC SERVER SYNC

- Migration applied on SERVER: `db/migrations/public/0003_public_auth_rbac.sql`
- Seed applied on SERVER: `db/seed/seed_public_auth_rbac_catalog_v0.2.4.sql`
- Resulting counts (SERVER):
  - roles = 68
  - permissions = 221
  - mappings = 1116



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).


### v0.2.47 — DB
- aircraft_utilization_ledger
- CHECK delta >= 0
- UNIQUE indexy wg source_ref.



### 2026-01-14 — stock_transactions idempotency (tenant-scoped)

- Replaced global uniqueness of `idempotency_key` with tenant-scoped unique index.
- Safe migration added (re-runnable): `2026-01-14_01_stock_transactions_idempotency_tenant_scoped.sql`.



### 2026-01-16 — DMS tenant migration
- Tenant migration added for DMS core tables: `db/migrations/tenant/0002_dms.sql`.
- Scope: document type registry + document instances + artifacts + audit events (tenant-scoped).
