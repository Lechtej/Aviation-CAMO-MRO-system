-- verify_import.sql (v0.2.3)

-- Tenants
SELECT code, tenant_type FROM public.tenants ORDER BY tenant_type, code;

-- Counts
SELECT count(*) AS aircraft_total FROM public.aircraft;
SELECT count(*) AS access_total FROM public.aircraft_mro_access;

SELECT t.code AS mro, count(*) AS aircraft_count
FROM public.aircraft_mro_access a
JOIN public.tenants t ON t.id=a.mro_tenant_id
GROUP BY t.code
ORDER BY t.code;

-- Missing MSN (informational)
SELECT count(*) AS aircraft_missing_msn
FROM public.aircraft
WHERE msn IS NULL OR msn = '';

-- Sanity checks for this dataset expectations (should return TRUE)
SELECT (SELECT count(*) FROM public.aircraft)=929 AS ok_aircraft_929;
SELECT (
  SELECT count(*)
  FROM public.aircraft_mro_access a
  JOIN public.tenants t ON t.id=a.mro_tenant_id
  WHERE t.code='lotams'
)=316 AS ok_lotams_316;

SELECT (
  SELECT count(*)
  FROM public.aircraft_mro_access a
  JOIN public.tenants t ON t.id=a.mro_tenant_id
  WHERE t.code='lst'
)=613 AS ok_lst_613;
