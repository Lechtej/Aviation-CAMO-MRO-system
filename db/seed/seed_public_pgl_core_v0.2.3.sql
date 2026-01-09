-- seed_public_pgl_core_v0.2.3.sql
-- Seeds PGL group and core tenants: LOTAMS, LST, LOT (CAMO).
-- Version: v0.2.3

BEGIN;

-- Group: PGL
INSERT INTO public.tenant_groups (code, name)
VALUES ('pgl', 'Polska Grupa Lotnicza')
ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name;

-- Tenants (codes are stable identifiers)
WITH g AS (SELECT id FROM public.tenant_groups WHERE code='pgl')
INSERT INTO public.tenants (group_id, code, name, tenant_type)
SELECT g.id, x.code, x.name, x.tenant_type::public.tenant_type
FROM g
CROSS JOIN (VALUES
  ('lotams', 'LOT Aircraft Maintenance Services (LOTAMS)', 'MRO'),
  ('lst',    'LS Technics', 'MRO'),
  ('lot',    'Polskie Linie Lotnicze LOT (PLL LOT)', 'CAMO')
) AS x(code, name, tenant_type)
ON CONFLICT (code) DO UPDATE SET
  name=EXCLUDED.name,
  tenant_type=EXCLUDED.tenant_type,
  group_id=EXCLUDED.group_id,
  updated_at=now();

-- Profiles
INSERT INTO public.mro_profiles (tenant_id, short_name)
SELECT id, 'LOTAMS' FROM public.tenants WHERE code='lotams'
ON CONFLICT (tenant_id) DO UPDATE SET short_name=EXCLUDED.short_name;

INSERT INTO public.mro_profiles (tenant_id, short_name)
SELECT id, 'LST' FROM public.tenants WHERE code='lst'
ON CONFLICT (tenant_id) DO UPDATE SET short_name=EXCLUDED.short_name;

INSERT INTO public.airline_profiles (tenant_id, iata_code, icao_code)
SELECT id, 'LO', 'LOT' FROM public.tenants WHERE code='lot'
ON CONFLICT (tenant_id) DO UPDATE SET iata_code=EXCLUDED.iata_code, icao_code=EXCLUDED.icao_code;

COMMIT;
