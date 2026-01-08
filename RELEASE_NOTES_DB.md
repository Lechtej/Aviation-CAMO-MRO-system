# AviationCAMO-MRO-system_DB — Release Notes (cumulative)

## v0.2.1 (2026-01-08)

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

## v0.2.2 — Merge with latest repo snapshot
- Merged DB baseline package with current repository snapshot (kept latest server/API docs).
- Preserved existing app files; added DB migration + seed + audit documents.
