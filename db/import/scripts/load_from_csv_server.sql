-- load_from_csv_server.sql
-- Purpose: Import PGL fleet dataset CSVs into *server schema* (public schema layout on prod)
-- Target tables (public schema): tenants, aircraft, aircraft_mro_access
-- Source CSVs expected inside DB container: /tmp/import_staging/*.csv
-- Idempotency: safe to re-run (uses ON CONFLICT upserts)

BEGIN;

-- UUID generator (needed for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==== STAGING TABLES (server import) ====
DROP TABLE IF EXISTS public._stg_airline_customers;
CREATE TABLE public._stg_airline_customers (
  airline_code text,
  airline_name text,
  airline_iata text,
  airline_icao text
);

DROP TABLE IF EXISTS public._stg_mro_customers;
CREATE TABLE public._stg_mro_customers (
  mro_code text,
  airline_code text
);

DROP TABLE IF EXISTS public._stg_aircraft;
CREATE TABLE public._stg_aircraft (
  current_registration text,
  msn text,
  manufacturer text,
  type text,
  subtype text,
  model text,
  airline_code text
);

DROP TABLE IF EXISTS public._stg_aircraft_mro_access;
CREATE TABLE public._stg_aircraft_mro_access (
  aircraft_registration text,
  mro_code text
);

-- ==== COPY CSV -> STAGING ====
\copy public._stg_airline_customers FROM '/tmp/import_staging/airline_customers.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_mro_customers     FROM '/tmp/import_staging/mro_customers.csv'      WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_aircraft          FROM '/tmp/import_staging/aircraft.csv'           WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_aircraft_mro_access FROM '/tmp/import_staging/aircraft_mro_access.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- ==== TENANTS UPSERTS ====
-- 1) Ensure airline tenants exist (exclude 'lot' because it is platform/CAMO tenant in our baseline)
INSERT INTO public.tenants (id, code, name, schema_name)
SELECT gen_random_uuid(), s.airline_code, s.airline_name, 't_'||s.airline_code
FROM public._stg_airline_customers s
LEFT JOIN public.tenants t ON t.code = s.airline_code
WHERE t.id IS NULL AND s.airline_code <> 'lot'
ON CONFLICT (code) DO UPDATE SET
  name        = EXCLUDED.name,
  schema_name = EXCLUDED.schema_name;

-- 2) Ensure MRO tenants exist (if they are missing in DB)
INSERT INTO public.tenants (id, code, name, schema_name)
SELECT gen_random_uuid(), s.mro_code, upper(s.mro_code), 't_'||s.mro_code
FROM (SELECT DISTINCT mro_code FROM public._stg_mro_customers WHERE mro_code IS NOT NULL AND btrim(mro_code) <> '') s
LEFT JOIN public.tenants t ON t.code = s.mro_code
WHERE t.id IS NULL
ON CONFLICT (code) DO NOTHING;

-- 3) Contract-level MRO ↔ airline customers (optional table; only if it exists)
DO $$
BEGIN
  IF to_regclass('public.mro_customers') IS NOT NULL THEN
    INSERT INTO public.mro_customers (mro_tenant_id, customer_tenant_id)
    SELECT m.id, c.id
    FROM public._stg_mro_customers s
    JOIN public.tenants m ON m.code = s.mro_code
    JOIN public.tenants c ON c.code = s.airline_code
    ON CONFLICT (mro_tenant_id, customer_tenant_id) DO NOTHING;
  END IF;
END $$;

-- ==== AIRCRAFT UPSERT (server schema) ====
-- Map CSV -> server columns:
-- - registration  <- current_registration
-- - serial_number <- msn
-- - aircraft_type <- model/subtype/type (best available)
-- - status_tech   <- 'IN_SERVICE'
INSERT INTO public.aircraft (id, owner_tenant_id, registration, aircraft_type, serial_number, status_tech, notes)
SELECT
  gen_random_uuid(),
  t.id,
  a.current_registration,
  LEFT(COALESCE(NULLIF(a.model,''), NULLIF(a.subtype,''), NULLIF(a.type,'')), 64),
  LEFT(NULLIF(a.msn,''), 64),
  'IN_SERVICE',
  LEFT(CONCAT_WS(' | ',
        NULLIF(a.manufacturer,''),
        NULLIF(a.type,''),
        NULLIF(a.subtype,''),
        NULLIF(a.model,'')
      ), 1024)
FROM public._stg_aircraft a
JOIN public.tenants t ON t.code = a.airline_code
WHERE a.current_registration IS NOT NULL AND btrim(a.current_registration) <> ''
ON CONFLICT (owner_tenant_id, registration) DO UPDATE SET
  aircraft_type  = COALESCE(EXCLUDED.aircraft_type, public.aircraft.aircraft_type),
  serial_number  = COALESCE(EXCLUDED.serial_number, public.aircraft.serial_number),
  notes          = COALESCE(EXCLUDED.notes, public.aircraft.notes);

-- ==== AIRCRAFT ↔ MRO ACCESS (server schema) ====
-- Join by registration + owner_tenant_id (airline_code) and mro_code
INSERT INTO public.aircraft_mro_access (id, aircraft_id, mro_tenant_id, role, active)
SELECT
  gen_random_uuid(),
  ac.id,
  mro.id,
  'MAINTENANCE',
  true
FROM public._stg_aircraft_mro_access s
JOIN public._stg_aircraft a
  ON a.current_registration = s.aircraft_registration
JOIN public.tenants owner
  ON owner.code = a.airline_code
JOIN public.aircraft ac
  ON ac.owner_tenant_id = owner.id AND ac.registration = s.aircraft_registration
JOIN public.tenants mro
  ON mro.code = s.mro_code
ON CONFLICT (aircraft_id, mro_tenant_id) DO UPDATE SET
  active = true,
  role   = EXCLUDED.role;

-- ==== CLEANUP STAGING ====
DROP TABLE public._stg_airline_customers;
DROP TABLE public._stg_mro_customers;
DROP TABLE public._stg_aircraft;
DROP TABLE public._stg_aircraft_mro_access;

COMMIT;
