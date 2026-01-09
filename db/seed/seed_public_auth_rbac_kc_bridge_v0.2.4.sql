-- seed_public_auth_rbac_kc_bridge_v0.2.4.sql
-- Bridge Keycloak realm roles -> DB RBAC catalog (public.auth_roles / auth_role_permissions)
-- Idempotent: rebuilds mappings for bridge roles only.

BEGIN;

-- 1) Ensure bridge roles exist (codes match Keycloak realm roles)
WITH roles(code,name,scope,description) AS (
    VALUES
      ('AUDITOR','Auditor','tenant','Keycloak bridge: read-only/audit role (view/export/report only)'),
      ('CERTIFYING_STAFF','Certifying Staff','domain','Keycloak bridge: generic certifying staff role (legacy KC role)')
),
upsert AS (
    INSERT INTO public.auth_roles(code,name,scope,description,is_system)
    SELECT code,name,scope,description,true FROM roles
    ON CONFLICT (code) DO UPDATE
      SET name=EXCLUDED.name,
          scope=EXCLUDED.scope,
          description=EXCLUDED.description,
          updated_at=now()
    RETURNING id, code
)
SELECT count(*) AS bridge_roles_upserted FROM upsert;

-- 2) Clear existing mappings only for these bridge roles
WITH bridge_roles AS (
    SELECT id FROM public.auth_roles WHERE code IN ('AUDITOR','CERTIFYING_STAFF')
),
deleted AS (
    DELETE FROM public.auth_role_permissions rp
    USING bridge_roles br
    WHERE rp.role_id = br.id
    RETURNING 1
)
SELECT count(*) AS bridge_mappings_deleted FROM deleted;

-- 3) AUDITOR permissions (read-only-ish)
WITH br AS (SELECT id FROM public.auth_roles WHERE code='AUDITOR'),
perm AS (
    SELECT id FROM public.auth_permissions
    WHERE code LIKE '%.view'
       OR code LIKE '%.export'
       OR code LIKE '%.report%'
       OR code LIKE '%.read'
       OR code LIKE '%.list'
),
ins AS (
    INSERT INTO public.auth_role_permissions(role_id, permission_id)
    SELECT (SELECT id FROM br), perm.id
    FROM perm
    ON CONFLICT DO NOTHING
    RETURNING 1
)
SELECT count(*) AS auditor_mappings_inserted FROM ins;

-- 4) CERTIFYING_STAFF permissions (MRO prefix + dashboard view if exists)
WITH br AS (SELECT id FROM public.auth_roles WHERE code='CERTIFYING_STAFF'),
perm AS (
    SELECT id FROM public.auth_permissions
    WHERE code LIKE 'mro.%'
       OR code IN ('common.dashboard.view')
),
ins AS (
    INSERT INTO public.auth_role_permissions(role_id, permission_id)
    SELECT (SELECT id FROM br), perm.id
    FROM perm
    ON CONFLICT DO NOTHING
    RETURNING 1
)
SELECT count(*) AS certstaff_mappings_inserted FROM ins;

COMMIT;
