from __future__ import annotations

from fastapi import HTTPException, Request

# Role model:
# - JWT roles are extracted from Keycloak 'realm_access.roles'
# - We keep it simple and explicit for v0.2.44.

CAMO_ROLES = {
    "CAMO_PLANNER",
    "CAMO_ENGINEER",
    "TENANT_ADMIN",
    "PLATFORM_ADMIN",
}

MRO_ROLES = {
    "MAINT_PLANNER",
    "MECHANIC",
    "CERTIFYING_STAFF",
    "TENANT_ADMIN",
    "PLATFORM_ADMIN",
}

def _roles_from_request(request: Request) -> set[str]:
    auth = getattr(request.state, "auth", None)
    if not auth:
        return set()
    roles = getattr(auth, "roles", None) or []
    return {str(r) for r in roles}

def require_any_role(request: Request, allowed_roles: set[str], *, message: str = "Forbidden") -> None:
    roles = _roles_from_request(request)
    if roles.intersection(allowed_roles):
        return
    raise HTTPException(status_code=403, detail=message)

def require_camo(request: Request) -> None:
    require_any_role(request, CAMO_ROLES, message="Missing CAMO role")

def require_mro(request: Request) -> None:
    require_any_role(request, MRO_ROLES, message="Missing MRO role")

def require_camo_or_mro(request: Request) -> None:
    require_any_role(request, CAMO_ROLES.union(MRO_ROLES), message="Missing CAMO/MRO role")
