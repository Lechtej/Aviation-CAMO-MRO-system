-- AviationCAMO-MRO-system_DB_v0.2.1
-- Public (shared-across-tenants) tables for orgs/tenants and aircraft registry.
-- Apply in public schema (default). Recommended: psql -v ON_ERROR_STOP=1 -f this_file.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---- Tenant groups (e.g., Polish Aviation Group / PGL)
CREATE TABLE IF NOT EXISTS public.tenant_groups (
  id uuid PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ---- Tenants (organizations)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tenant_type') THEN
    CREATE TYPE public.tenant_type AS ENUM ('MRO','CAMO','AIRLINE_CUSTOMER');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.tenants (
  id uuid PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  tenant_type public.tenant_type NOT NULL,
  group_id uuid NULL REFERENCES public.tenant_groups(id) ON DELETE SET NULL,
  schema_name text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Airline-specific profile (optional)
CREATE TABLE IF NOT EXISTS public.airline_profiles (
  tenant_id uuid PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
  iata varchar(8),
  icao varchar(8),
  callsign varchar(64),
  country varchar(64)
);

-- MRO-specific profile (optional)
CREATE TABLE IF NOT EXISTS public.mro_profiles (
  tenant_id uuid PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
  short_name varchar(64),
  country varchar(64)
);

-- Relations: which MRO serves which airline customer
CREATE TABLE IF NOT EXISTS public.mro_customers (
  id uuid PRIMARY KEY,
  mro_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  customer_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_mro_customer UNIQUE (mro_tenant_id, customer_tenant_id)
);

-- ---- Aircraft registry (owned by an airline tenant; shared for all tenants)
CREATE TABLE IF NOT EXISTS public.aircraft (
  id uuid PRIMARY KEY,
  owner_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
  registration varchar(16) NOT NULL,
  msn varchar(32),
  manufacturer varchar(64),
  model varchar(64),
  aircraft_type varchar(64),
  subtype varchar(64),
  status_tech varchar(16) NOT NULL DEFAULT 'IN_SERVICE',
  notes varchar(1024),
  source_url text,
  retrieved_at_utc timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_aircraft_owner_registration UNIQUE (owner_tenant_id, registration),
  CONSTRAINT ck_aircraft_status_tech CHECK (status_tech IN ('IN_SERVICE','AOG','MAINTENANCE','STORED'))
);

-- Service access relation: which MRO tenant can work on which aircraft
CREATE TABLE IF NOT EXISTS public.aircraft_mro_access (
  id uuid PRIMARY KEY,
  aircraft_id uuid NOT NULL REFERENCES public.aircraft(id) ON DELETE CASCADE,
  mro_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
  role varchar(32) NOT NULL DEFAULT 'MRO_EDITOR',
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_aircraft_mro_access UNIQUE (aircraft_id, mro_tenant_id)
);

-- Optional: maintenance events (global)
CREATE TABLE IF NOT EXISTS public.aircraft_maintenance_events (
  id uuid PRIMARY KEY,
  aircraft_id uuid NOT NULL REFERENCES public.aircraft(id) ON DELETE CASCADE,
  title varchar(128) NOT NULL,
  event_type varchar(64),
  description text,
  planned_start_at timestamptz,
  planned_end_at timestamptz,
  status varchar(16) NOT NULL DEFAULT 'OPEN',
  mro_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_maint_event_status CHECK (status IN ('OPEN','PLANNED','IN_PROGRESS','DONE','CANCELLED'))
);

