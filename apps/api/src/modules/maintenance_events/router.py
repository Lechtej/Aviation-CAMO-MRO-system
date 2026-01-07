from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from modules.core.rbac import require_camo_or_mro
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.db import engine, get_db_session

from modules.aircraft import models as aircraft_models
from .schemas import MaintenanceEventCreate, MaintenanceEventOut


router = APIRouter(prefix="/v1/maintenance-events", tags=["Maintenance Events"], dependencies=[Depends(require_camo_or_mro)])


def _require_tenant_id(request: Request) -> UUID:
    tenant = getattr(request.state, "tenant", None)
    if not tenant or not getattr(tenant, "tenant_id", None):
        raise HTTPException(status_code=403, detail="Tenant context missing")
    return UUID(str(tenant.tenant_id))


def _ensure_tables() -> None:
    """Ensure required PUBLIC tables exist and have required columns."""
    # Base tables
    aircraft_models.Aircraft.__table__.create(bind=engine, checkfirst=True)
    aircraft_models.AircraftMroAccess.__table__.create(bind=engine, checkfirst=True)
    aircraft_models.AircraftMaintenanceEvent.__table__.create(bind=engine, checkfirst=True)

    # Lightweight "migration" for local dev: add event_type column if missing.
    # This is safe and idempotent on Postgres.
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE IF EXISTS public.aircraft_maintenance_events "
                "ADD COLUMN IF NOT EXISTS event_type VARCHAR(64)"
            )
        )


def _get_access(db: Session, tenant_id: UUID, aircraft_id: UUID):
    return (
        db.query(aircraft_models.AircraftMroAccess)
        .filter(aircraft_models.AircraftMroAccess.aircraft_id == aircraft_id)
        .filter(aircraft_models.AircraftMroAccess.mro_tenant_id == tenant_id)
        .filter(aircraft_models.AircraftMroAccess.active.is_(True))
        .first()
    )


@router.get("", response_model=List[MaintenanceEventOut])
def list_maintenance_events(
    request: Request,
    aircraft_id: UUID = Query(...),
    db: Session = Depends(get_db_session),
):
    """List maintenance events for an aircraft.

    Rules:
    - Owner tenant sees all events for the aircraft.
    - MRO tenant sees events only if it has active access to the aircraft.
      (For now: returns all events for the aircraft once access is granted.)
    - Tenants without access get an empty list (200 + []).
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    aircraft = db.get(aircraft_models.Aircraft, aircraft_id)
    if not aircraft:
        return []

    is_owner = UUID(str(aircraft.owner_tenant_id)) == tenant_id
    if not is_owner:
        access = _get_access(db, tenant_id, aircraft_id)
        if not access:
            return []

    rows = db.execute(
        text(
            """
            SELECT id, aircraft_id, created_by_tenant_id, event_type, description, status, created_at
            FROM public.aircraft_maintenance_events
            WHERE aircraft_id = :aircraft_id
            ORDER BY created_at DESC
            """
        ),
        {"aircraft_id": str(aircraft_id)},
    ).fetchall()

    return [
        MaintenanceEventOut(
            id=r.id,
            aircraft_id=r.aircraft_id,
            tenant_id=r.created_by_tenant_id,
            event_type=getattr(r, "event_type", None),
            description=r.description,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]

@router.post("", response_model=MaintenanceEventOut, status_code=201)
def create_maintenance_event(
    payload: MaintenanceEventCreate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Create maintenance event.

    Rules (per A5):
    - Owner can create.
    - MRO can create ONLY if it has active access AND role == MRO_EDITOR.
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    aircraft = db.get(aircraft_models.Aircraft, payload.aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    is_owner = UUID(str(aircraft.owner_tenant_id)) == tenant_id
    if not is_owner:
        access = _get_access(db, tenant_id, payload.aircraft_id)
        if not access:
            raise HTTPException(status_code=403, detail="No access to aircraft")
        if (access.role or "").upper() != "MRO_EDITOR":
            raise HTTPException(status_code=403, detail="MRO role does not allow creating maintenance events")

    ev = aircraft_models.AircraftMaintenanceEvent(
        aircraft_id=payload.aircraft_id,
        created_by_tenant_id=tenant_id,
        title=payload.event_type,
        description=payload.description,
        status=str(payload.status.value),
    )
    # optional column (added via _ensure_tables migration)
    setattr(ev, "event_type", payload.event_type)

    db.add(ev)
    db.commit()
    db.refresh(ev)

    return MaintenanceEventOut(
        id=ev.id,
        aircraft_id=ev.aircraft_id,
        tenant_id=ev.created_by_tenant_id,
        event_type=getattr(ev, "event_type", None),
        description=ev.description,
        status=ev.status,
        created_at=ev.created_at,
    )


@router.delete("/{event_id}", status_code=204)
def delete_maintenance_event(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Delete maintenance event (tenant-isolated).

    Rules:
    - Owner can delete any event for its aircraft.
    - Non-owner tenant can delete only events created by itself.
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    ev = db.get(aircraft_models.AircraftMaintenanceEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Maintenance event not found")

    aircraft = db.get(aircraft_models.Aircraft, ev.aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    is_owner = UUID(str(aircraft.owner_tenant_id)) == tenant_id
    if not is_owner and UUID(str(ev.created_by_tenant_id)) != tenant_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this event")

    db.delete(ev)
    db.commit()
    return Response(status_code=204)