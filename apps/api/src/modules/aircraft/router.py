from __future__ import annotations

from datetime import datetime

from fastapi import Response
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
    AircraftMaintenanceEventCreate,
    AircraftMaintenanceEventUpdate,
    AircraftMaintenanceEventOut,
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
    models.AircraftMaintenanceEvent.__table__.create(bind=engine, checkfirst=True)

    # Lightweight local-dev migration: add event_type column if missing.
    # Safe and idempotent on Postgres.
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE IF EXISTS public.aircraft_maintenance_events "
                "ADD COLUMN IF NOT EXISTS event_type VARCHAR(64)"
            )
        )


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


@router.get("/{aircraft_id}/maintenance-events", response_model=List[AircraftMaintenanceEventOut])
def list_maintenance_events(
    aircraft_id: UUID, request: Request, db: Session = Depends(get_db_session)
):
    """List maintenance events visible to the current tenant.

    Visible if:
    - current tenant is the aircraft owner (airline)
    - current tenant has active MRO access for the aircraft
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    aircraft = db.get(models.Aircraft, aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    owner = _is_owner(tenant_id, aircraft)
    mro = _has_mro_access(db, tenant_id, aircraft_id)
    if not owner and not mro:
        # hide existence
        raise HTTPException(status_code=404, detail="Aircraft not found")

    return (
        db.query(models.AircraftMaintenanceEvent)
        .filter(models.AircraftMaintenanceEvent.aircraft_id == aircraft_id)
        .order_by(models.AircraftMaintenanceEvent.created_at.desc())
        .all()
    )


@router.post(
    "/{aircraft_id}/maintenance-events",
    response_model=AircraftMaintenanceEventOut,
    status_code=201,
)
def create_maintenance_event(
    aircraft_id: UUID,
    payload: AircraftMaintenanceEventCreate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Create maintenance event (owner only)."""
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    aircraft = db.get(models.Aircraft, aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    if not _is_owner(tenant_id, aircraft):
        raise HTTPException(status_code=403, detail="Only owner tenant can create maintenance events")

    ev = models.AircraftMaintenanceEvent(
        aircraft_id=aircraft_id,
        created_by_tenant_id=tenant_id,
        title=payload.title,
        description=payload.description,
        status=str(payload.status.value),
        planned_start_at=payload.planned_start_at,
        planned_end_at=payload.planned_end_at,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.put(
    "/{aircraft_id}/maintenance-events/{event_id}",
    response_model=AircraftMaintenanceEventOut,
)
def update_maintenance_event(
    aircraft_id: UUID,
    event_id: UUID,
    payload: AircraftMaintenanceEventUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Update maintenance event.

    Scope:
    - owner can update any fields
    - MRO can update only: status, mro_notes
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    aircraft = db.get(models.Aircraft, aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    owner = _is_owner(tenant_id, aircraft)
    mro = _has_mro_access(db, tenant_id, aircraft_id)
    if not owner and not mro:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    ev = (
        db.query(models.AircraftMaintenanceEvent)
        .filter(models.AircraftMaintenanceEvent.id == event_id)
        .filter(models.AircraftMaintenanceEvent.aircraft_id == aircraft_id)
        .first()
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Maintenance event not found")

    if not owner:
        # MRO restrictions
        forbidden_fields = [
            payload.title,
            payload.description,
            payload.planned_start_at,
            payload.planned_end_at,
        ]
        if any(v is not None for v in forbidden_fields):
            raise HTTPException(
                status_code=400,
                detail="MRO tenant can update only: status, mro_notes",
            )

    # Owner fields
    if owner:
        if payload.title is not None:
            ev.title = payload.title
        if payload.description is not None:
            ev.description = payload.description
        if payload.planned_start_at is not None:
            ev.planned_start_at = payload.planned_start_at
        if payload.planned_end_at is not None:
            ev.planned_end_at = payload.planned_end_at

    # Shared / MRO fields
    if payload.status is not None:
        ev.status = str(payload.status.value)
    if payload.mro_notes is not None:
        ev.mro_notes = payload.mro_notes
    ev.updated_at = datetime.utcnow()

    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


