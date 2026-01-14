-- 0004_public_aircraft_utilization.sql
-- Public aircraft utilization tracking (FH/FC) + counters snapshot + aircraft dates.
-- Version: v0.2.4
--
-- Goals:
-- - Append-only utilization ledger for auditability (no in-place edits)
-- - Fast reads via counters snapshot (total_fh/total_fc)
-- - Optional aircraft dates to derive "age" (manufacture / entry-into-service)

BEGIN;

-- Extend aircraft master with optional dates (age is derived)
ALTER TABLE IF EXISTS public.aircraft
  ADD COLUMN IF NOT EXISTS manufacture_date date,
  ADD COLUMN IF NOT EXISTS entry_into_service_date date;

-- Append-only utilization ledger (delta FH/FC per day or per source record)
CREATE TABLE IF NOT EXISTS public.aircraft_utilization_ledger (
  id uuid PRIMARY KEY,
  aircraft_id uuid NOT NULL REFERENCES public.aircraft(id) ON DELETE CASCADE,
  op_date date NOT NULL,
  delta_fh numeric(10,2) NOT NULL DEFAULT 0,
  delta_fc integer NOT NULL DEFAULT 0,
  source varchar(32) NOT NULL DEFAULT 'MANUAL',
  source_ref varchar(128),
  notes varchar(1024),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_aircraft_util_delta_nonneg CHECK (delta_fh >= 0 AND delta_fc >= 0)
);

-- Uniqueness strategy:
-- - if source_ref is provided => unique per (aircraft, source, source_ref)
-- - otherwise => unique per (aircraft, op_date, source)
CREATE UNIQUE INDEX IF NOT EXISTS uq_aircraft_util_source_ref
  ON public.aircraft_utilization_ledger(aircraft_id, source, source_ref)
  WHERE source_ref IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_aircraft_util_by_date_source
  ON public.aircraft_utilization_ledger(aircraft_id, op_date, source)
  WHERE source_ref IS NULL;

CREATE INDEX IF NOT EXISTS ix_aircraft_util_aircraft_date
  ON public.aircraft_utilization_ledger(aircraft_id, op_date);

-- Snapshot counters (fast access for planning/forecast)
CREATE TABLE IF NOT EXISTS public.aircraft_counters (
  aircraft_id uuid PRIMARY KEY REFERENCES public.aircraft(id) ON DELETE CASCADE,
  total_fh numeric(12,2) NOT NULL DEFAULT 0,
  total_fc integer NOT NULL DEFAULT 0,
  last_ledger_id uuid REFERENCES public.aircraft_utilization_ledger(id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_aircraft_counters_nonneg CHECK (total_fh >= 0 AND total_fc >= 0)
);

COMMIT;
