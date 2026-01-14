# PGL Fleet Import (v0.2.3)

Source of truth:
- `db/import/source/Floty_MRO_PGL_v1.1.1_FINAL.xlsx`
  - Full fleet is in sheet **Fleet_ALL** (929 rows; 316 LOTAMS; 613 LST; 0 unknown)

Columns expected in Fleet_ALL:
```
MRO, Airline, Airline_IATA, Airline_ICAO, Manufacturer, Type, Subtype, Model,
Registration, MSN, SourceURL, RetrievedAtUTC
```

## Data identity rules
- `Registration` is treated as the current unique aircraft key for this dataset (929 unique).
- `MSN` is optional and missing for ~466 rows; when present it is stored and can be used later for history/merge.

## Run import
1. Run migrations + seed core tenants (PGL / LOTAMS / LST / LOT)
2. Generate CSV exports from XLSX and import into Postgres.

Use:
- `db/import/run_import.bat` (Windows) or run commands from the README below.

## Verification (must pass)
- Total aircraft: 929
- Aircraft MRO mapping rows: 929 (from this dataset)
- LOTAMS: 316
- LST: 613
- Unknown: 0

See `db/import/scripts/verify_import.sql`.



---

## Server (Hetzner) – import do aktualnego schematu produkcyjnego

**Problem:** serwer ma inny schemat DB niż lokalny (m.in. `aircraft.registration` zamiast `aircraft.current_registration`, brak `airline_profiles`, brak `mro_customers`).

**Pliki:**
- `db/import/scripts/load_from_csv_server.sql` – import do schematu serwera.
- `db/import/scripts/verify_import_server.sql` – weryfikacja integralności po imporcie.

### Procedura wdrożenia (prod/Hetzner)

**0) Wejście na serwer**
```bash
ssh root@65.108.250.169
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker
```

**1) Backup DB (host)**
```bash
docker compose exec -T db bash -lc 'mkdir -p /tmp/db_backups && pg_dump -U aviation -d aviation -Fc > /tmp/db_backups/aviation_before_import_$(date +%F_%H%M%S).dump && ls -lh /tmp/db_backups/*.dump | tail -n 1'
```

**2) Skopiuj pliki staging na hosta**
Z Windows (PowerShell), z repo lokalnego:
```powershell
scp -r ".\db\import\staging" "root@65.108.250.169:/tmp/import_staging_src"
```

**3) Uporządkuj pliki na hoście i wgraj do kontenera DB**
Na serwerze:
```bash
rm -rf /tmp/import_staging
mkdir -p /tmp/import_staging
# pliki staging są w /tmp/import_staging_src/(staging)? – kopiujemy katalog wykryty po load_from_csv.sql
SRC_DIR="$(dirname "$(find /tmp/import_staging_src -maxdepth 4 -type f -name load_from_csv.sql | head -n 1)")"
if [ -z "$SRC_DIR" ]; then SRC_DIR="/tmp/import_staging_src"; fi
cp -a "$SRC_DIR/." /tmp/import_staging/

# do kontenera DB
docker cp /tmp/import_staging/. docker-db-1:/tmp/import_staging
```

**4) Dedup aircraft.csv → aircraft_dedup.csv (w kontenerze DB)**
Na serwerze:
```bash
docker compose exec -T db bash -lc '
set -euo pipefail
psql -U aviation -d aviation -v ON_ERROR_STOP=1   -c "DROP TABLE IF EXISTS public._stg_aircraft_csv; CREATE TABLE public._stg_aircraft_csv (current_registration text, msn text, manufacturer text, type text, subtype text, model text, airline_code text);"   -c "\\copy public._stg_aircraft_csv FROM '''/tmp/import_staging/aircraft.csv''' WITH (FORMAT csv, HEADER true);"   -c "DROP TABLE IF EXISTS public._stg_aircraft_dedup; CREATE TABLE public._stg_aircraft_dedup AS
      SELECT current_registration, msn, manufacturer, type, subtype, model, airline_code
      FROM (
        SELECT s.*,
               ROW_NUMBER() OVER (
                 PARTITION BY COALESCE(NULLIF(s.msn,''''),
                                       ''REG:''||s.current_registration)
                 ORDER BY s.current_registration
               ) AS rn
        FROM public._stg_aircraft_csv s
      ) q
      WHERE rn=1;"   -c "\\copy (SELECT * FROM public._stg_aircraft_dedup ORDER BY current_registration) TO '''/tmp/import_staging/aircraft_dedup.csv''' WITH (FORMAT csv, HEADER true);"   -c "SELECT (SELECT COUNT(*) FROM public._stg_aircraft_csv) AS src_rows, (SELECT COUNT(*) FROM public._stg_aircraft_dedup) AS dedup_rows;"   -c "DROP TABLE public._stg_aircraft_csv; DROP TABLE public._stg_aircraft_dedup;"
'
```

**5) Import (server schema)**
Skopiuj z repo do serwera lub uruchom z ścieżki w repo (po wdrożeniu zmian w repo na serwer). Najprościej:
```bash
docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -v csvdir=/tmp/import_staging -f /tmp/import_staging/load_from_csv_server.sql
```
> `load_from_csv_server.sql` może być skopiowany do `/tmp/import_staging/` razem z CSV lub uruchamiany z repo: `-f db/import/scripts/load_from_csv_server.sql` (gdy repo na serwerze jest aktualne).

**6) Verify**
```bash
docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -f db/import/scripts/verify_import_server.sql
```

### Oczekiwane wyniki (na podstawie wdrożenia 2026-01-09)
- `public.tenants`: 41
- `public.aircraft`: 878
- `public.aircraft_mro_access`: 878
- `orphan_access`: 0


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

## 2026-01-14 — Baseline aircraft import (PGL XLSX) + MRO access mapping

### Cel
- Ustabilizować **bazę referencyjną AIRCRAFT** po imporcie PGL XLSX oraz udostępnić aircraft do tenantów MRO na podstawie kolumny `mro` w stagingu.
- Zapewnić deterministyczne wyniki endpointu `GET /v1/aircraft` dla tenantów: **LOT (owner)**, **LOTAMS (MRO)**, **LST (MRO / LS Technics)**.

### Założenia / ograniczenia modelu
- `public.aircraft.owner_tenant_id` jest **NOT NULL**.
- Unikalność aircraft: `uq_aircraft_owner_registration (owner_tenant_id, registration)` — **nie ma** unikalności samego `registration`.  
  Konsekwencja: `ON CONFLICT(registration)` nie działa (brak constraintu) — używaj konflików na `(owner_tenant_id, registration)` lub własnego warunku `WHERE NOT EXISTS`.

### Mapowanie MRO (staging → tenant)
Źródło: `public.staging_aircraft_pgl_full.mro` (normalizacja `upper()`):
- `LOTAMS` → tenant LOTAMS
- `LS TECHNICS` → tenant LST

Tabela docelowa: `public.aircraft_mro_access(aircraft_id, mro_tenant_id, role, active)`  
Constraint: `uq_aircraft_mro_access (aircraft_id, mro_tenant_id)`.

### UPSERT dostępu MRO z stagingu
Przykład (uruchamiane w `infra/docker`):

```sql
WITH map AS (
  SELECT 'LOTAMS'::text AS mro_norm, '<LOTAMS_UUID>'::uuid AS mro_tenant_id
  UNION ALL
  SELECT 'LS TECHNICS'::text AS mro_norm, '<LST_UUID>'::uuid AS mro_tenant_id
),
src AS (
  SELECT a.id AS aircraft_id, m.mro_tenant_id
  FROM public.staging_aircraft_pgl_full s
  JOIN map m ON upper(s.mro) = m.mro_norm
  JOIN public.aircraft a ON upper(a.registration) = upper(s.registration)
)
INSERT INTO public.aircraft_mro_access (id, aircraft_id, mro_tenant_id, role, active)
SELECT gen_random_uuid(), aircraft_id, mro_tenant_id, 'MRO', true
FROM src
ON CONFLICT (aircraft_id, mro_tenant_id)
DO UPDATE SET active=true, role='MRO';
```

### Obsługa brakującego aircraft w `public.aircraft`
Wykryto 1 rekord staging bez odpowiednika w `public.aircraft` (przykład: `OH-LWM`).

**Decyzja (baseline):**
- dodać technicznego właściciela `tenants.code='unk'` (`UNKNOWN_OWNER`) + schema `t_unk`
- wstawić aircraft z `owner_tenant_id=unk`, `operator_tenant_id=unk`
- dodać wpis w `aircraft_mro_access` dla tenant LST

Minimalne SQL:

```sql
-- 1) create UNKNOWN tenant (once)
INSERT INTO public.tenants (id, code, name, schema_name)
SELECT gen_random_uuid(), 'unk', 'UNKNOWN_OWNER', 't_unk'
WHERE NOT EXISTS (SELECT 1 FROM public.tenants WHERE code='unk');

CREATE SCHEMA IF NOT EXISTS t_unk;

-- 2) insert missing aircraft for owner=unk (example OH-LWM)
WITH s AS (
  SELECT upper(registration) AS reg, nullif(model,'') AS model_name, nullif(msn,'') AS msn
  FROM public.staging_aircraft_pgl_full
  WHERE upper(registration)='OH-LWM'
  LIMIT 1
),
unk AS (SELECT id AS tenant_id FROM public.tenants WHERE code='unk' LIMIT 1),
ins AS (
  INSERT INTO public.aircraft (
    id, owner_tenant_id, operator_tenant_id,
    registration, aircraft_type, serial_number,
    status_tech, notes
  )
  SELECT
    gen_random_uuid(),
    unk.tenant_id, unk.tenant_id,
    s.reg,
    COALESCE(s.model_name, 'UNKNOWN'),
    s.msn,
    'IN_SERVICE',
    'baseline_import_pgl_xlsx_2026-01-14'
  FROM s, unk
  RETURNING id
)
SELECT COUNT(*) FROM ins;

-- 3) grant MRO access (LST)
WITH a AS (
  SELECT id AS aircraft_id FROM public.aircraft WHERE upper(registration)='OH-LWM' LIMIT 1
)
INSERT INTO public.aircraft_mro_access (id, aircraft_id, mro_tenant_id, role, active)
SELECT gen_random_uuid(), a.aircraft_id, '<LST_UUID>'::uuid, 'MRO', true
FROM a
ON CONFLICT (aircraft_id, mro_tenant_id)
DO UPDATE SET active=true, role='MRO';
```

### Walidacja przez API
```bash
TOKEN="$(./get_token_dev.sh)"
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <LOT_UUID>"    "https://api.forgemotionsystems.com/v1/aircraft" | jq 'length'
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <LOTAMS_UUID>" "https://api.forgemotionsystems.com/v1/aircraft" | jq 'length'
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <LST_UUID>"    "https://api.forgemotionsystems.com/v1/aircraft" | jq 'length'
```

Oczekiwane (na bazie stagingu z 2026-01-14):
- LOT: ~52 aircraft (głównie `SP-*`)
- LOTAMS: 316 aircraft
- LST: 613 aircraft (w tym `OH-LWM`)
