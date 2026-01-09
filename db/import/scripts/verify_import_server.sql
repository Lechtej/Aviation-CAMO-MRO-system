-- verify_import_server.sql
-- Basic integrity checks for SERVER schema import (Hetzner).
\set ON_ERROR_STOP on

-- 1) Core row counts (should be > 0 after import)
SELECT
  (SELECT COUNT(*) FROM public.tenants) AS tenants,
  (SELECT COUNT(*) FROM public.aircraft) AS aircraft,
  (SELECT COUNT(*) FROM public.aircraft_mro_access) AS aircraft_mro_access;

-- 2) No orphan access rows
SELECT COUNT(*) AS orphan_access
FROM public.aircraft_mro_access ama
LEFT JOIN public.aircraft a ON a.id = ama.aircraft_id
WHERE a.id IS NULL;

-- 3) No empty registrations
SELECT
  COUNT(*) FILTER (WHERE registration IS NULL OR btrim(registration)='') AS empty_registration,
  COUNT(*) AS total_aircraft
FROM public.aircraft;

-- 4) Duplicates by registration within owner (should be 0 due to constraint)
SELECT owner_tenant_id, registration, COUNT(*) AS c
FROM public.aircraft
GROUP BY owner_tenant_id, registration
HAVING COUNT(*) > 1
ORDER BY c DESC
LIMIT 10;

-- 5) Access rows should reference existing tenants
SELECT COUNT(*) AS orphan_mro_tenant
FROM public.aircraft_mro_access ama
LEFT JOIN public.tenants t ON t.id = ama.mro_tenant_id
WHERE t.id IS NULL;
