from __future__ import annotations

"""DB-backed RBAC (permissions).

Contract
- JWT roles are extracted by modules.core.security into request.state.auth.roles
- Roles map to permissions in DB tables:
  - public.auth_roles(code,...)
  - public.auth_permissions(code,...)
  - public.auth_role_permissions(role_id, permission_id)

Implementation notes
- Uses a short sync query via SQLAlchemy SessionLocal.
- Caches resolved permissions on request.state._perms_cache.
"""

from typing import Iterable, Set

from fastapi import HTTPException, Request
from sqlalchemy import bindparam, text

from shared.db import SessionLocal


def _roles_from_request(request: Request) -> set[str]:
    auth = getattr(request.state, "auth", None)
    if not auth:
        return set()
    roles = getattr(auth, "roles", None) or []
    return {str(r) for r in roles}


def resolve_permissions_for_roles(role_codes: Iterable[str]) -> set[str]:
    roles = {str(r) for r in role_codes if str(r)}
    if not roles:
        return set()

    stmt = (
        text(
            """
            SELECT DISTINCT p.code
            FROM public.auth_permissions p
            JOIN public.auth_role_permissions rp ON rp.permission_id = p.id
            JOIN public.auth_roles r ON r.id = rp.role_id
            WHERE r.code IN :roles
            """
        )
        .bindparams(bindparam("roles", expanding=True))
    )

    with SessionLocal() as db:
        rows = db.execute(stmt, {"roles": sorted(list(roles))}).fetchall()

    return {str(r[0]) for r in rows if r and r[0]}


def get_request_permissions(request: Request) -> set[str]:
    """Return permission codes for current request.

    Caches in request.state._perms_cache to avoid repeated DB hits.
    """

    cached = getattr(request.state, "_perms_cache", None)
    if isinstance(cached, set):
        return cached

    roles = _roles_from_request(request)
    perms = resolve_permissions_for_roles(roles)
    request.state._perms_cache = perms
    return perms


def require_permission(request: Request, permission_code: str, *, message: str | None = None) -> None:
    """Raise 403 if permission is missing."""

    perms = get_request_permissions(request)
    if permission_code in perms:
        return

    raise HTTPException(
        status_code=403,
        detail=message or f"Missing permission: {permission_code}",
    )
