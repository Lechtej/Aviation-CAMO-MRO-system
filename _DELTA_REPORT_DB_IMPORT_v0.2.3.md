# Delta report — DB import tooling + documentation (v0.2.3)

Base: `Aviation-AMO-MRO-system- clean 1 do 1 z git repo www`
Delta source: `Aviation-AMO-MRO-system repo lokalne przed commit ze zmianami w bazie danych`

## Added (new files/folders)
- `db/import/` — complete XLSX→CSV→Postgres import tooling (README, scripts, staging SQL, source XLSX, export/staging CSV)
- `db/migrations/public/0001_public_core.sql`
- `db/migrations/public/0002_public_aircraft_registration_history.sql`
- `db/seed/seed_public_pgl_core_v0.2.3.sql`
- `scripts/xlsx_to_csv.py`

## Updated
- `docs/01_architecture/database_pgl_import.md`
  - added import stabilization note (dedup MSN → aircraft 928, access 928, orphan_access 0)
- `docs/master/AVIATION_CAMO_MRO_MASTER_DOC.md`
  - added link note to PGL fleet import documentation
- `RELEASE_NOTES_DB.md`
  - appended v0.2.3 entry with tooling + validated counts

## No deletions
- No files removed from the WWW-clean base; documentation history preserved.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
