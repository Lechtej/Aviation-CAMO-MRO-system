-- 0002_public_aircraft_registration_history.sql
-- Adds registration history for aircraft.
-- Version: v0.2.3

BEGIN;

CREATE TABLE IF NOT EXISTS public.aircraft_registration_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aircraft_id uuid NOT NULL REFERENCES public.aircraft(id) ON DELETE CASCADE,
  registration text NOT NULL,
  valid_from date NOT NULL DEFAULT CURRENT_DATE,
  valid_to date NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- One active registration per aircraft (valid_to IS NULL)
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_hist_one_active_per_aircraft
  ON public.aircraft_registration_history(aircraft_id)
  WHERE valid_to IS NULL;

-- Registration strings should not overlap globally as active (optional but useful)
CREATE UNIQUE INDEX IF NOT EXISTS ux_reg_hist_active_registration_unique
  ON public.aircraft_registration_history(registration)
  WHERE valid_to IS NULL;

COMMIT;
