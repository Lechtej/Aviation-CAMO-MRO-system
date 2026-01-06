# AviationCAMO-MRO v0.2.28 — Tenant Isolation (Inventory / Parts)

## Why
A confirmed data leak allowed Tenant B to see `Parts` created by Tenant A via `GET /v1/inventory/parts`.

## Changes
### DB
- `public.parts`
  - added column `tenant_id uuid` (nullable; transitional migration step)
  - added index `idx_parts_tenant_id` on `(tenant_id)`

### API
- All `/v1/inventory/parts*` endpoints are now tenant-scoped.
  - **CREATE** writes `tenant_id` from the resolved tenant context.
  - **LIST** filters by `tenant_id`.
  - **GET/UPDATE/DELETE** only operate within the caller's tenant (otherwise `404`).
- Requests without a resolved tenant context are rejected with `403 Tenant context missing`.

## Notes / Limitations
- `tenant_id` is nullable to allow a safe transition. Records with `tenant_id = NULL` will not be returned by tenant-scoped list queries.
- Existing unique constraint on `part_number` remains global (not per-tenant) in this version.

## How to test (A vs B)
1. Obtain tokens for Tenant A and Tenant B (token must contain `tenant_id` claim or use `X-Tenant-Id` only with `PLATFORM_ADMIN`).
2. Tenant A: `POST /v1/inventory/parts` (create a new part).
3. Tenant B: `GET /v1/inventory/parts`.

Expected: Tenant B does **not** see Tenant A's part.
