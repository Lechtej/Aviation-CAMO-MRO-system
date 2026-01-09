-- load_from_csv_server.sql
-- Purpose: Import PGL fleet CSVs into SERVER schema (current prod DB on Hetzner).
-- Notes:
-- - Server DB schema differs from local dev schema (aircraft.registration vs current_registration, etc.).
-- - Uses pgcrypto/gen_random_uuid() for UUIDs.
-- - Expects CSVs in directory set by :csvdir (default: /tmp/import_staging).

\set ON_ERROR_STOP on
\set csvdir '/tmp/import_staging'

BEGIN;

-- UUID generator
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- === STAGING TABLES (server) ===
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

-- Source aircraft.csv columns: current_registration, msn, manufacturer, type, subtype, model, airline_code
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

-- Source aircraft_mro_access.csv columns: current_registration, mro_code
DROP TABLE IF EXISTS public._stg_aircraft_mro_access;
CREATE TABLE public._stg_aircraft_mro_access (
  aircraft_registration text,
  mro_code text
);

\copy public._stg_airline_customers FROM :'csvdir'/airline_customers.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_mro_customers     FROM :'csvdir'/mro_customers.csv     WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_aircraft          FROM :'csvdir'/aircraft_dedup.csv    WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy public._stg_aircraft_mro_access FROM :'csvdir'/aircraft_mro_access.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- === TENANTS (server table has: id, code, name, schema_name, created_at) ===
-- 1) Ensure airline tenants exist (exclude 'lot' per dataset convention)
INSERT INTO public.tenants (id, code, name, schema_name)
SELECT gen_random_uuid(), s.airline_code, s.airline_name, 't_'||s.airline_code
FROM public._stg_airline_customers s
LEFT JOIN public.tenants t ON t.code = s.airline_code
WHERE t.id IS NULL AND s.airline_code <> 'lot'
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  schema_name = EXCLUDED.schema_name;

-- 2) Ensure MRO tenants exist (name defaults to code)
INSERT INTO public.tenants (id, code, name, schema_name)
SELECT gen_random_uuid(), s.mro_code, upper(s.mro_code), 't_'||s.mro_code
FROM public._stg_mro_customers s
LEFT JOIN public.tenants t ON t.code = s.mro_code
WHERE t.id IS NULL
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  schema_name = EXCLUDED.schema_name;

-- === AIRCRAFT (server table columns) ===
-- Table: public.aircraft(id, owner_tenant_id, registration, aircraft_type, serial_number, status_tech, notes)
INSERT INTO public.aircraft (
  id,
  owner_tenant_id,
  registration,
  aircraft_type,
  serial_number,
  status_tech,
  notes
)
SELECT
  gen_random_uuid(),
  t.id,
  a.current_registration,
  COALESCE(NULLIF(a.model,''), NULLIF(a.subtype,''), NULLIF(a.type,'')),
  NULLIF(a.msn,''),
  'IN_SERVICE',
  NULLIF(
    concat_ws(' | ',
      NULLIF(a.manufacturer,''),
      NULLIF(a.type,''),
      NULLIF(a.subtype,''),
      NULLIF(a.model,'')
    ),
    ''
  )
FROM public._stg_aircraft a
JOIN public.tenants t ON t.code = a.airline_code
ON CONFLICT (owner_tenant_id, registration) DO UPDATE SET
  aircraft_type = COALESCE(EXCLUDED.aircraft_type, public.aircraft.aircraft_type),
  serial_number = COALESCE(EXCLUDED.serial_number, public.aircraft.serial_number),
  status_tech   = COALESCE(EXCLUDED.status_tech, public.aircraft.status_tech),
  notes         = COALESCE(EXCLUDED.notes, public.aircraft.notes);

-- === AIRCRAFT ↔ MRO ACCESS (server) ===
-- Table: public.aircraft_mro_access(id, aircraft_id, mro_tenant_id, role, active)
INSERT INTO public.aircraft_mro_access (id, aircraft_id, mro_tenant_id, role, active)
SELECT
  gen_random_uuid(),
  ac.id,
  mro.id,
  'MAINTENANCE',
  true
FROM public._stg_aircraft_mro_access s
JOIN public.aircraft ac ON ac.registration = s.aircraft_registration
JOIN public.tenants  mro ON mro.code = s.mro_code
ON CONFLICT (aircraft_id, mro_tenant_id) DO UPDATE SET
  active = true,
  role   = EXCLUDED.role;

-- cleanup staging
DROP TABLE public._stg_airline_customers;
DROP TABLE public._stg_mro_customers;
DROP TABLE public._stg_aircraft;
DROP TABLE public._stg_aircraft_mro_access;

COMMIT;
