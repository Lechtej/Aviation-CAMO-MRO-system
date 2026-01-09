# Database: PGL Tenants & Fleet Import (v0.2.3)

## Tenants (public)
Tenants are organisations, all grouped under **PGL** for our project scope:

- `lotams` (tenant_type = MRO)
- `lst` (tenant_type = MRO)
- `lot` (tenant_type = CAMO) — also acts as airline owner/operator for LOT fleet

Additional airlines from the dataset are created as `AIRLINE_CUSTOMER` tenants (code derived primarily from ICAO/IATA).

## Aircraft identity rules
- Current dataset uniqueness is by `Registration` (929 unique).
- `MSN` is stored when available (466 rows in the dataset have missing MSN).
- `public.aircraft_registration_history` is initialized with the current registration per aircraft;
  future changes can be recorded by closing the active row (`valid_to`) and creating a new active row.

## Multi-MRO servicing
One aircraft may be serviced by multiple MRO providers (e.g., LOTAMS in WAW and LST in KTW).
This is represented by `public.aircraft_mro_access` (many-to-many), with optional scoping:
- `base_airport_iata`
- `valid_from`, `valid_to`

## How to apply (Windows)
Run from repo root:
- `db\import\run_import.bat`

## Verification
After import, run:
- `db/import/scripts/verify_import.sql`

Expected (Fleet_ALL):
- aircraft_total: 929
- LOTAMS: 316
- LST: 613
- unknown: 0
