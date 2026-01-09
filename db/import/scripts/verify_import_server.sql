-- verify_import_server.sql
-- Purpose: Post-import verification for PGL fleet dataset.
-- Works with BOTH schemas:
-- - server schema: public.aircraft.registration
-- - legacy/local schema: public.aircraft.current_registration
-- Output: counts + integrity checks; exits non-zero on failure (ON_ERROR_STOP recommended)

\set ON_ERROR_STOP on

-- 1) quick presence checks
SELECT
  (SELECT COUNT(*) FROM public.tenants)            AS tenants,
  (SELECT COUNT(*) FROM public.aircraft)           AS aircraft,
  (SELECT COUNT(*) FROM public.aircraft_mro_access) AS aircraft_mro_access;

-- 2) orphan access rows (must be 0)
SELECT COUNT(*) AS orphan_access
FROM public.aircraft_mro_access ama
LEFT JOIN public.aircraft a ON a.id = ama.aircraft_id
WHERE a.id IS NULL;

-- 3) validate registration/current_registration not empty (dynamic; supports both schemas)
DO $$
DECLARE
  col text;
  sql text;
  empty_cnt bigint;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='aircraft' AND column_name='registration'
  ) THEN
    col := 'registration';
  ELSIF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='aircraft' AND column_name='current_registration'
  ) THEN
    col := 'current_registration';
  ELSE
    RAISE EXCEPTION 'Neither public.aircraft.registration nor public.aircraft.current_registration exists';
  END IF;

  sql := format('SELECT COUNT(*) FROM public.aircraft WHERE %I IS NULL OR btrim(%I::text)=''''', col, col);
  EXECUTE sql INTO empty_cnt;

  RAISE NOTICE 'empty_%: %', col, empty_cnt;
  IF empty_cnt <> 0 THEN
    RAISE EXCEPTION 'FAILED: empty % values found: %', col, empty_cnt;
  END IF;
END $$;

-- 4) duplicates by (owner_tenant_id, registration/current_registration) (should be 0; unique constraint should enforce)
DO $$
DECLARE
  col text;
  sql text;
  dup_cnt bigint;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='aircraft' AND column_name='registration') THEN
    col := 'registration';
  ELSE
    col := 'current_registration';
  END IF;

  sql := format('
    SELECT COUNT(*) FROM (
      SELECT owner_tenant_id, %I, COUNT(*) c
      FROM public.aircraft
      GROUP BY owner_tenant_id, %I
      HAVING COUNT(*)>1
    ) q', col, col);

  EXECUTE sql INTO dup_cnt;

  RAISE NOTICE 'duplicate_owner_%: %', col, dup_cnt;
  IF dup_cnt <> 0 THEN
    RAISE EXCEPTION 'FAILED: duplicates found for owner_tenant_id + %: %', col, dup_cnt;
  END IF;
END $$;
