from __future__ import annotations

"""Tenant context plumbing (v0.2.2)

Goal:
- Resolve the active tenant for each request
- Provide a deterministic mapping to PostgreSQL schema-per-tenant

Security note:
- Token validation is NOT enforced yet (plumbing only).
- In production, tenant context MUST come from verified OIDC token claims.
"""

from dataclasses import dataclass
from uuid import UUID

from .tenants_repo import get_schema_name_for_tenant_id

FALLBACK_SCHEMA_PREFIX = "t_"  # fallback schema name: t_<tenant_uuid_without_dashes>


def _fallback_schema_name_for_tenant_id(tenant_id: str) -> str:
    tid = str(UUID(tenant_id))
    compact = tid.replace("-", "")
    return f"{FALLBACK_SCHEMA_PREFIX}{compact}"


def schema_name_for_tenant_id(tenant_id: str) -> str:
    """Resolve schema name for a tenant.

    - Primary: lookup in public.tenants (schema_name)
    - Fallback: deterministic UUID-based schema (t_<uuid_without_dashes>)
    """
    tid = str(UUID(tenant_id))
    found = get_schema_name_for_tenant_id(tid)
    return found or _fallback_schema_name_for_tenant_id(tid)

@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    schema: str
    source: str  # e.g. header, token, debug

def build_tenant_context(tenant_id: str, source: str) -> TenantContext:
    return TenantContext(
        tenant_id=str(UUID(tenant_id)),
        schema=schema_name_for_tenant_id(tenant_id),
        source=source,
    )
