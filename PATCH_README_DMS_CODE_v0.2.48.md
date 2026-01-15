# DMS CODE PATCH v0.2.48 (changed files only)

## What this patch delivers
- Tenant migration for DMS tables.
- FastAPI module `modules/dms` with MVP endpoints.
- Wiring into API app.
- Append-only updates to `README.md` and `RELEASE_NOTES.md`.

## Files included
- `db/migrations/tenant/0002_dms.sql`
- `apps/api/src/main.py`
- `apps/api/src/modules/dms/models.py`
- `apps/api/src/modules/dms/schemas.py`
- `apps/api/src/modules/dms/router.py`
- `README.md`
- `RELEASE_NOTES.md`

## Apply
1) Copy files preserving paths into your repo.
2) Apply migration in target tenant schema (example):
   - `psql -v ON_ERROR_STOP=1 -d aviation -U aviation -f db/migrations/tenant/0002_dms.sql`
   - Ensure `search_path` is set to the tenant schema when executing.
3) Restart API.

## Smoke test (example)
- Create type: POST `/v1/dms/types`
- Create document: POST `/v1/dms/documents`
- Transition: POST `/v1/dms/documents/{id}/issue`
