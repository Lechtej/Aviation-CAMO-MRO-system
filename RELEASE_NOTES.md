# AviationCAMO-MRO — Release Notes (cumulative)

## v0.2.2 — packaging + docs alignment (2026-01-08)
- README/docs: ujednolicone odniesienia wersji do v0.2.2 (ZIP snapshot)
- Packaging: ZIP now matches GitHub repo root layout (no extra wrapper folder, single `RELEASE_NOTES.md` at repo root).
- Docs: moved `docs/SERVER_SMOKE_TEST_KEYCLOAK_OIDC.md` into `docs/03_ops/` to keep all server/OIDC smoke-test material together.

## v0.2.1 (2026-01-08) — DB baseline packaging

### Database (multi-tenant PGL)
- Added shared `public` tenant model for the Polish Aviation Group (PGL):
  - `public.tenant_groups` (group), `public.tenants` (tenant), `tenant_type` = `MRO | CAMO | AIRLINE_CUSTOMER`
  - profiles: `public.airline_profiles`, `public.mro_profiles`
  - customer mapping: `public.mro_customers`
- Added aircraft registry in `public`:
  - `public.aircraft` (ownership by airline tenant)
  - `public.aircraft_mro_access` (which MRO tenants can service which aircraft)
  - `public.aircraft_maintenance_events` (optional global events)
- Seeded PGL tenants:
  - `LOTAMS` (MRO), `LST` (MRO), `LOT` (CAMO; PLL LOT)
- Imported initial airline customers and LOT fleet dataset:
  - Source file: `Floty_MRO_PGL_v1.1.1.xlsx` (import based on sheet `Fleet_SAMPLE`, because `Fleet` sheet is empty)
  - Granted servicing access for LOTAMS + LST to all imported LOT aircraft
- Deliverables:
  - Migration: `db/migrations/public/0001_public_tenants_aircraft.sql`
  - Seed: `db/seed/seed_public_pgl_tenants_and_lot_fleet_v0.2.1.sql`
  - Audit note: `DB_AUDIT.md`

### Docs
- Added DB-specific packaging notes for server workstreams (this DB package is compatible with server deployment work; it does not imply the application code regressed from later versions).
