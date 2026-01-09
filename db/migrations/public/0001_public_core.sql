-- 0001_public_core.sql
-- Public/shared schema objects for multi-tenant setup and aircraft registry.
-- Version: v0.2.3
--
-- Notes:
-- - public.tenants represents organisations (MRO, CAMO, Airline customers).
-- - Aircraft are stored in public to allow cross-tenant visibility and service mapping.
-- - Identity strategy:
--     * current_registration is REQUIRED and UNIQUE (matches dataset uniqueness).
--     * msn is OPTIONAL; when present we keep it and may use it for future merge/history logic.

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tenant_type') THEN
    CREATE TYPE public.tenant_type AS ENUM ('MRO', 'CAMO', 'AIRLINE_CUSTOMER');
  END IF;
END$$;

-- Tenant groups (e.g., "Polska Grupa Lotnicza")
CREATE TABLE IF NOT EXISTS public.tenant_groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Tenants (MRO / CAMO / Airline customers)
CREATE TABLE IF NOT EXISTS public.tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id uuid NULL REFERENCES public.tenant_groups(id) ON DELETE SET NULL,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  tenant_type public.tenant_type NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Profiles (optional extensions)
CREATE TABLE IF NOT EXISTS public.airline_profiles (
  tenant_id uuid PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
  iata_code text NULL,
  icao_code text NULL
);

CREATE TABLE IF NOT EXISTS public.mro_profiles (
  tenant_id uuid PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
  short_name text NULL
);

-- Which MRO serves which airline customer (contract-level relation)
CREATE TABLE IF NOT EXISTS public.mro_customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mro_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  customer_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (mro_tenant_id, customer_tenant_id)
);

-- Aircraft registry (MSN = technical identity, registration = mutable)
CREATE TABLE IF NOT EXISTS public.aircraft (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Technical immutable identifier
  msn text NULL,

  -- Current operational registration (can change over time)
  current_registration text NOT NULL,

  manufacturer text NULL,
  type text NULL,
  subtype text NULL,
  model text NULL,

  -- owner/operator are tenants (typically airline customer; LOT is CAMO tenant but also airline owner in our setup)
  owner_tenant_id uuid NULL REFERENCES public.tenants(id) ON DELETE SET NULL,
  operator_tenant_id uuid NULL REFERENCES public.tenants(id) ON DELETE SET NULL,

  status text NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Ensure current registration uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS ux_aircraft_current_registration
  ON public.aircraft (current_registration);

-- Ensure that if MSN exists, it is unique (but allow NULL/empty)
CREATE UNIQUE INDEX IF NOT EXISTS ux_aircraft_msn_not_null
  ON public.aircraft (msn)
  WHERE msn IS NOT NULL AND msn <> '';

-- Aircraft ↔ MRO access mapping (many-to-many; one aircraft may be served by multiple MROs)
CREATE TABLE IF NOT EXISTS public.aircraft_mro_access (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aircraft_id uuid NOT NULL REFERENCES public.aircraft(id) ON DELETE CASCADE,
  mro_tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Optional scoping for "where" / "when" this MRO serves the aircraft
  base_airport_iata text NULL,
  valid_from date NOT NULL DEFAULT CURRENT_DATE,
  valid_to date NULL,

  created_at timestamptz NOT NULL DEFAULT now()
);

-- Replace invalid UNIQUE(...COALESCE...) with two partial unique indexes:
-- 1) base_airport_iata IS NULL
CREATE UNIQUE INDEX IF NOT EXISTS ux_aircraft_mro_access_null_base
  ON public.aircraft_mro_access (aircraft_id, mro_tenant_id, valid_from)
  WHERE base_airport_iata IS NULL;

-- 2) base_airport_iata IS NOT NULL
CREATE UNIQUE INDEX IF NOT EXISTS ux_aircraft_mro_access_with_base
  ON public.aircraft_mro_access (aircraft_id, mro_tenant_id, base_airport_iata, valid_from)
  WHERE base_airport_iata IS NOT NULL;

COMMIT;
