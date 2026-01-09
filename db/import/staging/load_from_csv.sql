-- load_from_csv.sql (v0.2.3)
-- Loads CSV exports into staging tables and merges into public tables.
--
-- Usage (psql):
--   \set csvdir 'db/import/export'
--   \i db/import/staging/load_from_csv.sql

BEGIN;

-- Staging tables
CREATE TEMP TABLE stg_airline_customers (
  airline_code text,
  airline_name text,
  airline_iata text,
  airline_icao text
);

CREATE TEMP TABLE stg_mro_customers (
  mro_code text,
  airline_code text
);

CREATE TEMP TABLE stg_aircraft (
  current_registration text,
  msn text,
  manufacturer text,
  type text,
  subtype text,
  model text,
  airline_code text
);

CREATE TEMP TABLE stg_aircraft_mro_access (
  current_registration text,
  mro_code text
);

-- Load CSVs (requires psql \set csvdir ...)
\copy stg_airline_customers FROM :'csvdir'/airline_customers.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy stg_mro_customers FROM :'csvdir'/mro_customers.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy stg_aircraft FROM :'csvdir'/aircraft.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy stg_aircraft_mro_access FROM :'csvdir'/aircraft_mro_access.csv WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

-- Ensure airline tenants exist
INSERT INTO public.tenants (group_id, code, name, tenant_type)
SELECT tg.id, s.airline_code, s.airline_name, 'AIRLINE_CUSTOMER'::public.tenant_type
FROM stg_airline_customers s
LEFT JOIN public.tenants t ON t.code = s.airline_code
JOIN public.tenant_groups tg ON tg.code = 'pgl'
WHERE t.id IS NULL AND s.airline_code <> 'lot'
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  tenant_type = EXCLUDED.tenant_type,
  group_id = EXCLUDED.group_id,
  updated_at = now();

-- Airline profiles
INSERT INTO public.airline_profiles (tenant_id, iata_code, icao_code)
SELECT t.id, NULLIF(s.airline_iata,''), NULLIF(s.airline_icao,'')
FROM stg_airline_customers s
JOIN public.tenants t ON t.code = s.airline_code
ON CONFLICT (tenant_id) DO UPDATE SET
  iata_code = EXCLUDED.iata_code,
  icao_code = EXCLUDED.icao_code;

-- Contract-level MRO ↔ airline customers
INSERT INTO public.mro_customers (mro_tenant_id, customer_tenant_id)
SELECT m.id, c.id
FROM stg_mro_customers s
JOIN public.tenants m ON m.code = s.mro_code
JOIN public.tenants c ON c.code = s.airline_code
ON CONFLICT (mro_tenant_id, customer_tenant_id) DO NOTHING;

-- Upsert aircraft (by current_registration for this dataset)
INSERT INTO public.aircraft (
  current_registration, msn, manufacturer, type, subtype, model, owner_tenant_id, operator_tenant_id
)
SELECT
  a.current_registration,
  NULLIF(a.msn,''),
  NULLIF(a.manufacturer,''),
  NULLIF(a.type,''),
  NULLIF(a.subtype,''),
  NULLIF(a.model,''),
  t.id,
  t.id
FROM stg_aircraft a
JOIN public.tenants t ON t.code = a.airline_code
ON CONFLICT (current_registration) DO UPDATE SET
  msn = COALESCE(NULLIF(EXCLUDED.msn,''), public.aircraft.msn),
  manufacturer = COALESCE(EXCLUDED.manufacturer, public.aircraft.manufacturer),
  type = COALESCE(EXCLUDED.type, public.aircraft.type),
  subtype = COALESCE(EXCLUDED.subtype, public.aircraft.subtype),
  model = COALESCE(EXCLUDED.model, public.aircraft.model),
  owner_tenant_id = EXCLUDED.owner_tenant_id,
  operator_tenant_id = EXCLUDED.operator_tenant_id,
  updated_at = now();

-- Registration history bootstrap: ensure one active record for each aircraft (current_registration)
INSERT INTO public.aircraft_registration_history (aircraft_id, registration, valid_from, valid_to)
SELECT ac.id, ac.current_registration, CURRENT_DATE, NULL
FROM public.aircraft ac
LEFT JOIN public.aircraft_registration_history h
  ON h.aircraft_id = ac.id AND h.valid_to IS NULL
WHERE h.id IS NULL
ON CONFLICT DO NOTHING;

-- Aircraft ↔ MRO access
INSERT INTO public.aircraft_mro_access (aircraft_id, mro_tenant_id, base_airport_iata, valid_from, valid_to)
SELECT ac.id, m.id, NULL, CURRENT_DATE, NULL
FROM stg_aircraft_mro_access s
JOIN public.aircraft ac ON ac.current_registration = s.current_registration
JOIN public.tenants m ON m.code = s.mro_code
ON CONFLICT (aircraft_id, mro_tenant_id, COALESCE(base_airport_iata,''), valid_from) DO NOTHING;

COMMIT;
