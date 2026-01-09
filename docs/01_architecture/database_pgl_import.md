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

## Import stabilization note (2026-01-09)

During real import execution, the dataset contained at least one **duplicate MSN** while `public.aircraft` enforces uniqueness for non-null MSN (`ux_aircraft_msn_not_null`).
This causes `load_from_csv.sql` to fail on aircraft merge unless the input is deduplicated.

### Observed final counts (Postgres, public schema)
After applying dedup and re-running the import:
- `public.aircraft` = **928**
- `public.aircraft_mro_access` = **928**
- `orphan_access` (access without aircraft) = **0**

### Dedup rule used
Generate `aircraft_dedup.csv` from `aircraft.csv`:
- primary key: `msn` **when present**
- fallback key: `current_registration` (when `msn` is empty)

Result: `src_rows=929` → `dedup_rows=928`.

### Safe Docker-based import (Windows PowerShell)
When using Docker Compose DB container, avoid relying on `:'csvdir'` by rewriting paths inside the SQL to point at the container directory (example: `/tmp/import_staging`).

Validated sequence (high-signal):
1. Copy CSV files into DB container under `/tmp/import_staging/`.
2. Rewrite `\copy` paths in `load_from_csv.sql` to use `/tmp/import_staging/...`.
3. If import fails on MSN uniqueness: generate `/tmp/import_staging/aircraft_dedup.csv` and switch `stg_aircraft` source to the dedup file.
4. Run:
   - `psql -v ON_ERROR_STOP=1 -f /tmp/import_staging/load_from_csv.sql`
5. Validate:
   - `SELECT COUNT(*) FROM public.aircraft;` → 928
   - `SELECT COUNT(*) FROM public.aircraft_mro_access;` → 928
   - `SELECT COUNT(*) FROM public.aircraft_mro_access ama LEFT JOIN public.aircraft a ON a.id=ama.aircraft_id WHERE a.id IS NULL;` → 0

### Recommended follow-up
If business requires keeping 929 aircraft rows, revise the MSN uniqueness strategy (e.g., conditional unique, data cleansing, or conflict resolution policy) and re-run import.
