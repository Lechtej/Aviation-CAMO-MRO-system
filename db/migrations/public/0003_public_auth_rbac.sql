-- 0003_public_auth_rbac.sql
-- Purpose: Introduce DB-backed RBAC catalog (roles, permissions, mappings)
-- Scope: public schema (cross-tenant / shared catalog)
-- Idempotency: safe to re-run (CREATE TABLE IF NOT EXISTS + IF NOT EXISTS indexes)

BEGIN;

CREATE TABLE IF NOT EXISTS public.auth_roles (
    id            bigserial PRIMARY KEY,
    code          text NOT NULL UNIQUE,
    name          text NOT NULL,
    scope         text NOT NULL CHECK (scope IN ('platform','tenant','domain','system')),
    description   text,
    is_system     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.auth_permissions (
    id            bigserial PRIMARY KEY,
    code          text NOT NULL UNIQUE,
    domain        text NOT NULL,
    description   text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.auth_role_permissions (
    role_id       bigint NOT NULL REFERENCES public.auth_roles(id) ON DELETE CASCADE,
    permission_id bigint NOT NULL REFERENCES public.auth_permissions(id) ON DELETE CASCADE,
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_roles_scope ON public.auth_roles(scope);
CREATE INDEX IF NOT EXISTS idx_auth_permissions_domain ON public.auth_permissions(domain);
CREATE INDEX IF NOT EXISTS idx_auth_role_permissions_perm ON public.auth_role_permissions(permission_id);

COMMIT;
