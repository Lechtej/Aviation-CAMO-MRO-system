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
