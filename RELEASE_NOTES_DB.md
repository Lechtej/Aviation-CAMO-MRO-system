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
