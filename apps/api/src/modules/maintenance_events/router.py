from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from modules.core.rbac_db import require_permission, get_request_permissions
from shared.db import engine, get_db_session

from modules.aircraft import models as aircraft_models
from .repo import MaintenanceEventsRepo
from .schemas import MaintenanceEventCreate, MaintenanceEventOut, MaintenanceEventStatus, MaintenanceEventUpdate


router = APIRouter(prefix="/v1/maintenance-events", tags=["Maintenance Events"])


P_CAMO_CREATE = "camo.maintenance_events.create"
P_CAMO_READ = "camo.maintenance_events.read"
P_CAMO_CLOSE = "camo.maintenance_events.close"  # optional (not used in v0)

P_MRO_READ_ASSIGNED = "mro.maintenance_events.read_assigned"
P_MRO_UPDATE_STATUS = "mro.maintenance_events.update_status"


def _require_tenant_id(request: Request) -> UUID:
    tenant = getattr(request.state, "tenant", None)
    if not tenant or not getattr(tenant, "tenant_id", None):
        raise HTTPException(status_code=403, detail="Tenant context missing")
    return UUID(str(tenant.tenant_id))


def _ensure_tables() -> None:
    """Ensure required PUBLIC tables exist (dev-friendly, idempotent)."""
    aircraft_models.Aircraft.__table__.create(bind=engine, checkfirst=True)
    aircraft_models.AircraftMroAccess.__table__.create(bind=engine, checkfirst=True)
    aircraft_models.AircraftMaintenanceEvent.__table__.create(bind=engine, checkfirst=True)


def _allowed_transition(old: str, new: str) -> bool:
    old_u, new_u = (old or "").upper(), (new or "").upper()
    if old_u == "OPEN" and new_u == "IN_PROGRESS":
        return True
    if old_u == "IN_PROGRESS" and new_u == "DONE":
        return True
    # MVP: allow MRO to cancel any time before DONE
    if new_u == "CANCELLED" and old_u in ("OPEN", "IN_PROGRESS"):
        return True
    return False


@router.get("", response_model=List[MaintenanceEventOut])
def list_maintenance_events(
    request: Request,
    aircraft_id: Optional[UUID] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    """List maintenance events visible to current tenant.

    Visibility:
    - CAMO: aircraft.owner_tenant_id == tenant
    - MRO : aircraft_mro_access(active) exists for tenant
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)

    perms = get_request_permissions(request)
    allow_owner = P_CAMO_READ in perms
    allow_mro = P_MRO_READ_ASSIGNED in perms
    if not (allow_owner or allow_mro):
        raise HTTPException(status_code=403, detail="Missing permission to read maintenance events")

    repo = MaintenanceEventsRepo(db)
    rows = repo.list_visible_events(
        tenant_id=tenant_id,
        allow_owner=allow_owner,
        allow_mro_assigned=allow_mro,
        aircraft_id=aircraft_id,
        limit=limit,
    )
    return [MaintenanceEventOut(**r) for r in rows]


@router.post("", response_model=MaintenanceEventOut, status_code=201)
def create_maintenance_event(
    payload: MaintenanceEventCreate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Create maintenance event (CAMO owner only).

    Contract (EPIC2 v0): always created with status OPEN.
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    require_permission(request, P_CAMO_CREATE)

    repo = MaintenanceEventsRepo(db)
    owner_tenant_id = repo.aircraft_owner_tenant_id(payload.aircraft_id)
    if owner_tenant_id is None:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    if owner_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Only owner tenant can create maintenance events")

    ev = repo.create_event(
        aircraft_id=payload.aircraft_id,
        created_by_tenant_id=tenant_id,
        event_type=payload.event_type,
        description=payload.description,
    )
    db.commit()
    return MaintenanceEventOut(**ev)


@router.patch("/{event_id}", response_model=MaintenanceEventOut)
def patch_maintenance_event(
    event_id: UUID,
    payload: MaintenanceEventUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Update event (MRO assigned only).

    Allowed transitions (MVP):
    - OPEN -> IN_PROGRESS
    - IN_PROGRESS -> DONE
    - (optional) OPEN/IN_PROGRESS -> CANCELLED
    """
    _ensure_tables()
    tenant_id = _require_tenant_id(request)
    require_permission(request, P_MRO_UPDATE_STATUS)

    repo = MaintenanceEventsRepo(db)
    ev = repo.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Maintenance event not found")

    aircraft_id = UUID(str(ev["aircraft_id"]))
    if not repo.mro_has_access(tenant_id, aircraft_id):
        # IMPORTANT: even if tenant is owner, patch in EPIC2 is reserved for MRO flow.
        raise HTTPException(status_code=403, detail="No MRO access to aircraft")

    old_status = str(ev["status"]) if ev.get("status") is not None else ""
    new_status = str(payload.status.value)
    if not _allowed_transition(old_status, new_status):
        raise HTTPException(status_code=409, detail=f"Invalid status transition: {old_status} -> {new_status}")

    updated = repo.update_event_status(
        event_id=event_id,
        new_status=new_status,
        mro_notes=payload.mro_notes,
    )
    db.commit()
    return MaintenanceEventOut(**updated)
