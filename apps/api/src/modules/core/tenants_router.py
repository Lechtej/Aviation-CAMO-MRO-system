from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from .tenants_schemas import TenantCreate, TenantOut
from .tenants_repo import create_tenant, list_tenants


router = APIRouter(prefix="/v1/tenants", tags=["Core"])


def require_role(request: Request, role: str) -> None:
    auth = getattr(request.state, "auth", None)
    if not auth or role not in getattr(auth, "roles", []):
        raise HTTPException(status_code=403, detail=f"Missing role: {role}")


@router.get("", response_model=list[TenantOut])
def http_list_tenants(request: Request):
    require_role(request, "PLATFORM_ADMIN")
    return list_tenants()


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def http_create_tenant(payload: TenantCreate, request: Request):
    require_role(request, "PLATFORM_ADMIN")
    try:
        return create_tenant(code=payload.code, name=payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Tenant already exists (code must be unique)")
