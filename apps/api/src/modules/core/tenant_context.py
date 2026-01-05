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
import re

SCHEMA_PREFIX = "t_"  # schema name will be: t_<tenant_uuid_without_dashes>

def schema_name_for_tenant_id(tenant_id: str) -> str:
    # Normalize UUID (strip dashes). Validate format.
    tid = str(UUID(tenant_id))
    compact = tid.replace("-", "")
    return f"{SCHEMA_PREFIX}{compact}"

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
