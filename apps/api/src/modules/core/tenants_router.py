from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from .rbac_db import require_permission
from .tenants_repo import create_tenant, list_tenants
from .tenants_schemas import TenantCreate, TenantOut

router = APIRouter(prefix="/v1/tenants", tags=["Core"])


@router.get("", response_model=list[TenantOut])
def http_list_tenants(request: Request):
    # DB-backed permission check (public RBAC catalog)
    require_permission(request, "platform.tenants.view")
    return list_tenants()


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def http_create_tenant(payload: TenantCreate, request: Request):
    # DB-backed permission check (public RBAC catalog)
    require_permission(request, "platform.tenants.create")
    try:
        return create_tenant(code=payload.code, name=payload.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Tenant already exists (code must be unique)")
