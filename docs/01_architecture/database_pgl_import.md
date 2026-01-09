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



---

## Server schema (Hetzner) – różnice i import

Na serwerze (aktualny prod DB) schemat tabel różni się od lokalnego importu z tego repo. Dlatego import „lokalny” (`db/import/staging/load_from_csv.sql`) **nie** jest kompatybilny z serwerem.

### Najważniejsze różnice schematu

**Tenants**
- Server: `public.tenants(id, code, name, schema_name, created_at)`
- Brak na serverze: `group_id`, `tenant_type`, `updated_at` (które występują w lokalnym wariancie importu)

**Aircraft**
- Server: `public.aircraft(id, owner_tenant_id, registration, aircraft_type, serial_number, status_tech, notes)`
- Lokalnie: import celuje w kolumny typu `current_registration`, `operator_tenant_id`, `updated_at` itd. (nie istnieją na serverze)

**Relacje**
- Server ma `public.aircraft_mro_access` (jest), ale nie ma tabel: `public.airline_profiles`, `public.mro_customers`, `public.aircraft_registration_history` (w stanie z 2026-01-09).

### Wariant importu dla serwera

Używaj:
- `db/import/scripts/load_from_csv_server.sql`
- `db/import/scripts/verify_import_server.sql`

Źródłem danych są te same CSV z pipeline (`db/import/staging/*.csv`) + dodatkowo generowany `aircraft_dedup.csv` (deduplikacja po `msn` / `registration`).

### Minimalny runbook (serwer)

1. Skopiuj staging CSV na hosta: `/tmp/import_staging/`
2. Wgraj je do kontenera DB: `docker cp /tmp/import_staging/. docker-db-1:/tmp/import_staging`
3. Zrób `aircraft_dedup.csv` (patrz `db/import/README.md`, sekcja server)
4. Uruchom import:
   ```bash
   docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -v csvdir=/tmp/import_staging -f db/import/scripts/load_from_csv_server.sql
   ```
5. Uruchom weryfikację:
   ```bash
   docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -f db/import/scripts/verify_import_server.sql
   ```

### Snapshot z wdrożenia 2026-01-09 (prod)
- aircraft: 878
- aircraft_mro_access: 878
- tenants: 41
- orphan_access: 0
