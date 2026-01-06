from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.db import get_db_session
from modules.logistics import models
from modules.logistics.schemas import PartCreate, PartUpdate, PartOut


router = APIRouter(prefix="/v1/inventory", tags=["Inventory"])


def _require_tenant_id(request: Request) -> UUID:
    """Return current tenant_id from middleware context.

    Inventory endpoints must be tenant-scoped. If tenant context is missing,
    we deny access (prevents cross-tenant / global data exposure).
    """
    tenant = getattr(request.state, "tenant", None)
    if not tenant or not getattr(tenant, "tenant_id", None):
        raise HTTPException(status_code=403, detail="Tenant context missing")
    return UUID(str(tenant.tenant_id))


@router.get("/parts", response_model=List[PartOut])
def list_parts(request: Request, db: Session = Depends(get_db_session)):
    tenant_id = _require_tenant_id(request)
    return (
        db.query(models.Part)
        .filter(models.Part.tenant_id == tenant_id)
        .order_by(models.Part.part_number.asc())
        .all()
    )


@router.post("/parts", response_model=PartOut, status_code=201)
def create_part(payload: PartCreate, request: Request, db: Session = Depends(get_db_session)):
    tenant_id = _require_tenant_id(request)
    obj = models.Part(
        tenant_id=tenant_id,
        part_number=payload.part_number,
        description=payload.description,
        part_type=str(payload.part_type.value),
        uom_code=payload.uom_code,
        is_pool_item=payload.is_pool_item,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Part already exists (part_number must be unique)")
    db.refresh(obj)
    return obj


@router.get("/parts/{part_id}", response_model=PartOut)
def get_part(part_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    tenant_id = _require_tenant_id(request)
    obj = (
        db.query(models.Part)
        .filter(models.Part.id == part_id)
        .filter(models.Part.tenant_id == tenant_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Part not found")
    return obj


@router.put("/parts/{part_id}", response_model=PartOut)
def update_part(part_id: UUID, payload: PartUpdate, request: Request, db: Session = Depends(get_db_session)):
    tenant_id = _require_tenant_id(request)
    obj = (
        db.query(models.Part)
        .filter(models.Part.id == part_id)
        .filter(models.Part.tenant_id == tenant_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Part not found")

    if payload.description is not None:
        obj.description = payload.description
    if payload.part_type is not None:
        obj.part_type = str(payload.part_type.value)
    if payload.uom_code is not None:
        obj.uom_code = payload.uom_code
    if payload.is_pool_item is not None:
        obj.is_pool_item = payload.is_pool_item

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/parts/{part_id}", status_code=204)
def delete_part(part_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    tenant_id = _require_tenant_id(request)
    obj = (
        db.query(models.Part)
        .filter(models.Part.id == part_id)
        .filter(models.Part.tenant_id == tenant_id)
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(obj)
    db.commit()
    return None
