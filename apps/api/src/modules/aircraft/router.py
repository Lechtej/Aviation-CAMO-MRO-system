from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.db import get_db_session, engine

from . import models
from .schemas import (
    AircraftCreate,
    AircraftUpdateOwner,
    AircraftUpdateMro,
    AircraftOut,
    AircraftWithMroAccessOut,
    MroAccessCreate,
    MroAccessOut,
)


router = APIRouter(prefix="/v1/aircraft", tags=["Aircraft"])


def _require_tenant_id(request: Request) -> UUID:
    tenant = getattr(request.state, "tenant", None)
    if not tenant or not getattr(tenant, "tenant_id", None):
        raise HTTPException(status_code=403, detail="Tenant context missing")
    return UUID(str(tenant.tenant_id))


def _ensure_tables() -> None:
    """Create public Aircraft tables if missing.

    We keep this idempotent to simplify local development.
    In production, migrations should be used.
    """
    # Create ONLY aircraft-related tables.
    # Do not call Base.metadata.create_all() here because it would also create
    # tenant-scoped tables in the current search_path schema.
    models.Aircraft.__table__.create(bind=engine, checkfirst=True)
    models.AircraftMroAccess.__table__.create(bind=engine, checkfirst=True)


@router.post("/_admin/bootstrap", status_code=201)
def bootstrap_aircraft(request: Request, db: Session = Depends(get_db_session)):
    """Dev bootstrap: create Aircraft tables in public schema."""
    auth = getattr(request.state, "auth", None)
    if not auth or "PLATFORM_ADMIN" not in getattr(auth, "roles", []):
        raise HTTPException(status_code=403, detail="Missing role: PLATFORM_ADMIN")
    _ensure_tables()
    return {"status": "ok"}


def _is_owner(tenant_id: UUID, aircraft: models.Aircraft) -> bool:
    return UUID(str(aircraft.owner_tenant_id)) == tenant_id


def _has_mro_access(db: Session, tenant_id: UUID, aircraft_id: UUID) -> bool:
    return (
        db.query(models.AircraftMroAccess)
        .filter(models.AircraftMroAccess.aircraft_id == aircraft_id)
        .filter(models.AircraftMroAccess.mro_tenant_id == tenant_id)
        .filter(models.AircraftMroAccess.active.is_(True))
        .first()
        is not None
    )


@router.get("", response_model=List[AircraftOut])
def list_aircraft(request: Request, db: Session = Depends(get_db_session)):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    owned = db.query(models.Aircraft).filter(models.Aircraft.owner_tenant_id == tenant_id)

    accessible_ids = (
        db.query(models.AircraftMroAccess.aircraft_id)
        .filter(models.AircraftMroAccess.mro_tenant_id == tenant_id)
        .filter(models.AircraftMroAccess.active.is_(True))
        .subquery()
    )
    accessible = db.query(models.Aircraft).filter(models.Aircraft.id.in_(accessible_ids))

    # UNION ALL would require same entity; easiest: fetch ids and merge
    res = owned.order_by(models.Aircraft.registration.asc()).all()
    res2 = (
        accessible
        .filter(models.Aircraft.owner_tenant_id != tenant_id)
        .order_by(models.Aircraft.registration.asc())
        .all()
    )
    by_id = {r.id: r for r in res}
    for r in res2:
        by_id[r.id] = r
    return list(by_id.values())


@router.post("", response_model=AircraftOut, status_code=201)
def create_aircraft(payload: AircraftCreate, request: Request, db: Session = Depends(get_db_session)):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    obj = models.Aircraft(
        owner_tenant_id=tenant_id,
        registration=payload.registration,
        aircraft_type=payload.aircraft_type,
        serial_number=payload.serial_number,
        status_tech=str(payload.status_tech.value),
        notes=payload.notes,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Aircraft already exists (registration must be unique per owner)")
    db.refresh(obj)
    return obj


@router.get("/{aircraft_id}", response_model=AircraftWithMroAccessOut)
def get_aircraft(aircraft_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    if not _is_owner(tenant_id, obj) and not _has_mro_access(db, tenant_id, aircraft_id):
        raise HTTPException(status_code=404, detail="Aircraft not found")

    return obj


@router.put("/{aircraft_id}", response_model=AircraftOut)
def update_aircraft(
    aircraft_id: UUID,
    payload: AircraftUpdateOwner | AircraftUpdateMro,
    request: Request,
    db: Session = Depends(get_db_session),
):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    owner = _is_owner(tenant_id, obj)
    mro = _has_mro_access(db, tenant_id, aircraft_id)
    if not owner and not mro:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    # Enforce scope:
    if owner:
        if getattr(payload, "registration", None) is not None:
            obj.registration = payload.registration  # type: ignore[attr-defined]
        if getattr(payload, "aircraft_type", None) is not None:
            obj.aircraft_type = payload.aircraft_type  # type: ignore[attr-defined]
        if getattr(payload, "serial_number", None) is not None:
            obj.serial_number = payload.serial_number  # type: ignore[attr-defined]

    # Both owner and MRO can edit these (scope B)
    if getattr(payload, "status_tech", None) is not None:
        obj.status_tech = str(payload.status_tech.value)  # type: ignore[union-attr]
    if getattr(payload, "notes", None) is not None:
        obj.notes = payload.notes  # type: ignore[attr-defined]

    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict (registration must be unique per owner)")
    db.refresh(obj)
    return obj


@router.delete("/{aircraft_id}", status_code=204)
def delete_aircraft(aircraft_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    if not _is_owner(tenant_id, obj):
        raise HTTPException(status_code=403, detail="Only owner tenant can delete aircraft")
    db.delete(obj)
    db.commit()
    return None


@router.get("/{aircraft_id}/mro-access", response_model=List[MroAccessOut])
def list_mro_access(aircraft_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj or not _is_owner(tenant_id, obj):
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return (
        db.query(models.AircraftMroAccess)
        .filter(models.AircraftMroAccess.aircraft_id == aircraft_id)
        .order_by(models.AircraftMroAccess.mro_tenant_id.asc())
        .all()
    )


@router.post("/{aircraft_id}/mro-access", response_model=MroAccessOut, status_code=201)
def grant_mro_access(
    aircraft_id: UUID,
    payload: MroAccessCreate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj or not _is_owner(tenant_id, obj):
        raise HTTPException(status_code=404, detail="Aircraft not found")

    access = models.AircraftMroAccess(
        aircraft_id=aircraft_id,
        mro_tenant_id=payload.mro_tenant_id,
        role=payload.role,
        active=payload.active,
    )
    db.add(access)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="MRO access already exists")
    db.refresh(access)
    return access


@router.delete("/{aircraft_id}/mro-access/{access_id}", status_code=204)
def revoke_mro_access(
    aircraft_id: UUID,
    access_id: UUID,
    request: Request,
    db: Session = Depends(get_db_session),
):
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    obj = db.get(models.Aircraft, aircraft_id)
    if not obj or not _is_owner(tenant_id, obj):
        raise HTTPException(status_code=404, detail="Aircraft not found")

    access = (
        db.query(models.AircraftMroAccess)
        .filter(models.AircraftMroAccess.id == access_id)
        .filter(models.AircraftMroAccess.aircraft_id == aircraft_id)
        .first()
    )
    if not access:
        raise HTTPException(status_code=404, detail="Access not found")
    db.delete(access)
    db.commit()
    return None
