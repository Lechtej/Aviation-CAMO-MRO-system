from __future__ import annotations

from decimal import Decimal
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import text

from shared.db import get_db_session
from . import models
from .schemas import (
    PartCreate, PartUpdate, PartOut,
    WarehouseCreate, WarehouseUpdate, WarehouseOut,
    LocationCreate, LocationUpdate, LocationOut,
    StockItemCreate, StockItemUpdate, StockItemOut,
    UomOut,
    StockTransactionCreate, StockTransactionOut,
    StockReservationCreate, StockReservationOut,
)
from .bootstrap import bootstrap_shared_dictionaries, bootstrap_tenant_tables

router = APIRouter(prefix="/v1/logistics", tags=["Logistics"])


def require_role(request: Request, role: str) -> None:
    auth = getattr(request.state, "auth", None)
    if not auth or role not in getattr(auth, "roles", []):
        raise HTTPException(status_code=403, detail=f"Missing role: {role}")


@router.post("/_admin/bootstrap", status_code=201)
def bootstrap_logistics(request: Request, db: Session = Depends(get_db_session)):
    """Creates schemas/tables needed for Logistics (dev bootstrap)."""
    require_role(request, "PLATFORM_ADMIN")
    bootstrap_shared_dictionaries(db)
    bootstrap_tenant_tables()
    return {"status": "ok"}


@router.get("/uom", response_model=List[UomOut])
def list_uom(db: Session = Depends(get_db_session)):
    return db.query(models.Uom).order_by(models.Uom.code.asc()).all()


# PARTS
@router.get("/parts", response_model=List[PartOut])
def list_parts(db: Session = Depends(get_db_session)):
    return db.query(models.Part).order_by(models.Part.part_number.asc()).all()


@router.post("/parts", response_model=PartOut, status_code=201)
def create_part(payload: PartCreate, db: Session = Depends(get_db_session)):
    obj = models.Part(
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
def get_part(part_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Part, part_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Part not found")
    return obj


@router.put("/parts/{part_id}", response_model=PartOut)
def update_part(part_id: UUID, payload: PartUpdate, db: Session = Depends(get_db_session)):
    obj = db.get(models.Part, part_id)
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
def delete_part(part_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Part, part_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(obj)
    db.commit()
    return None


# WAREHOUSES
@router.get("/warehouses", response_model=List[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db_session)):
    return db.query(models.Warehouse).order_by(models.Warehouse.code.asc()).all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db_session)):
    obj = models.Warehouse(code=payload.code, name=payload.name, is_active=payload.is_active)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Warehouse already exists (code must be unique)")
    db.refresh(obj)
    return obj


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Warehouse, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return obj


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(warehouse_id: UUID, payload: WarehouseUpdate, db: Session = Depends(get_db_session)):
    obj = db.get(models.Warehouse, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    if payload.name is not None:
        obj.name = payload.name
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/warehouses/{warehouse_id}", status_code=204)
def delete_warehouse(warehouse_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Warehouse, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    db.delete(obj)
    db.commit()
    return None


# LOCATIONS
@router.get("/locations", response_model=List[LocationOut])
def list_locations(db: Session = Depends(get_db_session)):
    return db.query(models.Location).order_by(models.Location.code.asc()).all()


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db_session)):
    wh = db.get(models.Warehouse, payload.warehouse_id)
    if not wh:
        raise HTTPException(status_code=400, detail="warehouse_id does not exist")
    obj = models.Location(
        warehouse_id=payload.warehouse_id,
        code=payload.code,
        name=payload.name,
        is_active=payload.is_active,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Location already exists in this warehouse (code must be unique)")
    db.refresh(obj)
    return obj


@router.get("/locations/{location_id}", response_model=LocationOut)
def get_location(location_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Location, location_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")
    return obj


@router.put("/locations/{location_id}", response_model=LocationOut)
def update_location(location_id: UUID, payload: LocationUpdate, db: Session = Depends(get_db_session)):
    obj = db.get(models.Location, location_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")

    if payload.name is not None:
        obj.name = payload.name
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(location_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.Location, location_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(obj)
    db.commit()
    return None


# STOCK ITEMS
@router.get("/stock-items", response_model=List[StockItemOut])
def list_stock_items(db: Session = Depends(get_db_session)):
    return db.query(models.StockItem).all()


@router.post("/stock-items", response_model=StockItemOut, status_code=201)
def create_stock_item(payload: StockItemCreate, db: Session = Depends(get_db_session)):
    if not db.get(models.Part, payload.part_id):
        raise HTTPException(status_code=400, detail="part_id does not exist")
    if not db.get(models.Location, payload.location_id):
        raise HTTPException(status_code=400, detail="location_id does not exist")

    obj = models.StockItem(
        part_id=payload.part_id,
        location_id=payload.location_id,
        serial_number=payload.serial_number,
        condition=str(payload.condition.value),
        owner=payload.owner,
        qty_on_hand=payload.qty_on_hand,
        qty_reserved=payload.qty_reserved,
        qty_in_transit=payload.qty_in_transit,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Stock item already exists for (part, location, serial_number)")
    db.refresh(obj)
    return obj


@router.get("/stock-items/{stock_id}", response_model=StockItemOut)
def get_stock_item(stock_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.StockItem, stock_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return obj


@router.put("/stock-items/{stock_id}", response_model=StockItemOut)
def update_stock_item(stock_id: UUID, payload: StockItemUpdate, db: Session = Depends(get_db_session)):
    obj = db.get(models.StockItem, stock_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Stock item not found")
    if payload.location_id is not None:
        if not db.get(models.Location, payload.location_id):
            raise HTTPException(status_code=400, detail="location_id does not exist")
        obj.location_id = payload.location_id
    if payload.condition is not None:
        obj.condition = str(payload.condition.value)
    if payload.owner is not None:
        obj.owner = payload.owner
    if payload.qty_on_hand is not None:
        obj.qty_on_hand = payload.qty_on_hand
    if payload.qty_reserved is not None:
        obj.qty_reserved = payload.qty_reserved
    if payload.qty_in_transit is not None:
        obj.qty_in_transit = payload.qty_in_transit

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/stock-items/{stock_id}", status_code=204)
def delete_stock_item(stock_id: UUID, db: Session = Depends(get_db_session)):
    obj = db.get(models.StockItem, stock_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Stock item not found")
    db.delete(obj)
    db.commit()
    return None


# --- #13 STOCK RESERVATIONS (soft lock; does NOT change on-hand) ---

@router.get("/stock-reservations", response_model=List[StockReservationOut])
def list_stock_reservations(request: Request, db: Session = Depends(get_db_session)):
    ROLE_STORE = "LOGISTICS_OFFICER"
    ROLE_CAMO = "CAMO_PLANNER"
    ROLE_ADMIN = {"PLATFORM_ADMIN", "TENANT_ADMIN"}

    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing header: X-Tenant-Id")

    auth = getattr(request.state, "auth", None)
    roles = set(getattr(auth, "roles", [])) if auth else set()
    if not (roles & ROLE_ADMIN or ROLE_STORE in roles or ROLE_CAMO in roles):
        raise HTTPException(status_code=403, detail="Missing role for reservations")

    rows = db.execute(
        text(
            "SELECT id, created_at, created_by_user_id, created_by_username, tenant_id, status, "
            "warehouse_id, part_id, stock_item_id, qty_reserved, qty_consumed, uom, "
            "source_ref_type, source_ref_id, expires_at "
            "FROM public.stock_reservations "
            "WHERE tenant_id = CAST(:tenant_id AS uuid) "
            "ORDER BY created_at DESC "
            "LIMIT 200"
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()

    out: list[dict] = []
    for r in rows:
        out.append(
            {
                **r,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            }
        )
    return out


@router.post("/stock-reservations", response_model=StockReservationOut, status_code=201)
def create_stock_reservation(payload: StockReservationCreate, request: Request, db: Session = Depends(get_db_session)):
    ROLE_STORE = "LOGISTICS_OFFICER"
    ROLE_CAMO = "CAMO_PLANNER"
    ROLE_ADMIN = {"PLATFORM_ADMIN", "TENANT_ADMIN"}

    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing header: X-Tenant-Id")

    auth = getattr(request.state, "auth", None)
    roles = set(getattr(auth, "roles", [])) if auth else set()
    if not (roles & ROLE_ADMIN or ROLE_STORE in roles or ROLE_CAMO in roles):
        raise HTTPException(status_code=403, detail="Missing role for reservations")

    item = (
        db.query(models.StockItem)
        .filter(models.StockItem.id == payload.stock_item_id)
        .with_for_update()
        .one_or_none()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    qty = Decimal(str(payload.qty))
    on_hand = Decimal(str(item.qty_on_hand))
    reserved = Decimal(str(item.qty_reserved))
    avail = on_hand - reserved
    if avail < qty:
        raise HTTPException(status_code=409, detail="Insufficient available stock for reservation")

    loc = db.get(models.Location, item.location_id)
    if not loc:
        raise HTTPException(status_code=500, detail="Stock item location missing")
    part = db.get(models.Part, item.part_id)
    if not part:
        raise HTTPException(status_code=500, detail="Stock item part missing")
    uom = getattr(part, "uom_code", None) or "EA"

    created_by_user_id = str(getattr(auth, "sub", None) or getattr(auth, "user_id", None) or "unknown")
    created_by_username = getattr(auth, "username", None)

    rec = db.execute(
        text(
            "INSERT INTO public.stock_reservations ("
            "created_by_user_id, created_by_username, tenant_id, status, "
            "warehouse_id, part_id, stock_item_id, qty_reserved, qty_consumed, uom, "
            "source_ref_type, source_ref_id, expires_at"
            ") VALUES ("
            ":created_by_user_id, :created_by_username, CAST(:tenant_id AS uuid), 'OPEN', "
            "CAST(:warehouse_id AS uuid), CAST(:part_id AS uuid), CAST(:stock_item_id AS uuid), "
            ":qty_reserved, 0, :uom, :source_ref_type, CAST(:source_ref_id AS uuid), "
            "CASE WHEN :expires_at IS NULL OR :expires_at = '' THEN NULL ELSE CAST(:expires_at AS timestamptz) END"
            ") RETURNING id, created_at"
        ),
        {
            "created_by_user_id": created_by_user_id,
            "created_by_username": created_by_username,
            "tenant_id": tenant_id,
            "warehouse_id": str(loc.warehouse_id),
            "part_id": str(item.part_id),
            "stock_item_id": str(item.id),
            "qty_reserved": qty,
            "uom": uom,
            "source_ref_type": payload.source_ref_type,
            "source_ref_id": str(payload.source_ref_id),
            "expires_at": payload.expires_at or "",
        },
    ).mappings().first()

    item.qty_reserved = Decimal(str(item.qty_reserved)) + qty
    db.add(item)

    db.commit()
    db.refresh(item)

    return {
        "id": rec["id"],
        "created_at": rec["created_at"].isoformat() if rec["created_at"] else None,
        "created_by_user_id": created_by_user_id,
        "created_by_username": created_by_username,
        "tenant_id": UUID(tenant_id),
        "status": "OPEN",
        "warehouse_id": UUID(str(loc.warehouse_id)),
        "part_id": UUID(str(item.part_id)),
        "stock_item_id": UUID(str(item.id)),
        "qty_reserved": float(qty),
        "qty_consumed": 0.0,
        "uom": uom,
        "source_ref_type": payload.source_ref_type,
        "source_ref_id": payload.source_ref_id,
        "expires_at": payload.expires_at,
    }


# STOCK TRANSACTIONS
@router.post("/stock-transactions", response_model=StockTransactionOut, status_code=201)
def create_stock_transaction(payload: StockTransactionCreate, request: Request, db: Session = Depends(get_db_session)):
    ROLE_STORE = "LOGISTICS_OFFICER"
    ROLE_MECH = "MECHANIC"
    ROLE_CAMO = "CAMO_PLANNER"
    ROLE_ADMIN = {"PLATFORM_ADMIN", "TENANT_ADMIN"}

    tenant_id = request.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing header: X-Tenant-Id")
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        raise HTTPException(status_code=400, detail="Missing header: Idempotency-Key")

    auth = getattr(request.state, "auth", None)
    roles = set(getattr(auth, "roles", [])) if auth else set()

    t = payload.type.upper()

    # Role checks
    if roles & ROLE_ADMIN:
        pass
    elif t == "RECEIPT":
        if ROLE_STORE not in roles:
            raise HTTPException(status_code=403, detail="RECEIPT requires store role")
    elif t in ("ISSUE", "RETURN"):
        if ROLE_STORE in roles or ROLE_MECH in roles:
            pass
        elif t == "ISSUE" and ROLE_CAMO in roles:
            if not getattr(payload, "reservation_id", None):
                raise HTTPException(status_code=403, detail="CAMO_PLANNER ISSUE requires reservation_id")
        else:
            raise HTTPException(status_code=403, detail="Missing role for transaction")
    else:
        raise HTTPException(status_code=422, detail="Invalid transaction type")

    # Idempotency replay (tenant scoped)
    existing = db.execute(
        text(
            "SELECT id, stock_item_id FROM public.stock_transactions "
            "WHERE tenant_id = CAST(:tenant_id AS uuid) AND idempotency_key = :k"
        ),
        {"tenant_id": tenant_id, "k": idem_key},
    ).mappings().first()

    if existing:
        qty_on_hand = db.execute(
            text("SELECT qty_on_hand FROM public.stock_items WHERE id = CAST(:id AS uuid)"),
            {"id": str(existing["stock_item_id"])},
        ).scalar()
        return {
            "transaction_id": uuid4(),
            "stock_transaction_id": existing["id"],
            "stock_item_id": existing["stock_item_id"],
            "qty_on_hand": float(qty_on_hand) if qty_on_hand is not None else None,
        }

    qty = Decimal(str(payload.qty))

    # Lock stock item
    obj = (
        db.query(models.StockItem)
        .filter(models.StockItem.id == payload.stock_item_id)
        .with_for_update()
        .one_or_none()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Derive warehouse_id + uom
    loc = db.get(models.Location, obj.location_id)
    if not loc:
        raise HTTPException(status_code=500, detail="Stock item location missing")
    part = db.get(models.Part, obj.part_id)
    if not part:
        raise HTTPException(status_code=500, detail="Stock item part missing")
    uom = getattr(part, "uom_code", None) or "EA"

    # Reservation rules (ISSUE)
    reservation_id = getattr(payload, "reservation_id", None)
    if t == "ISSUE":
        if reservation_id:
            # lock reservation row
            r = db.execute(
                text(
                    "SELECT id, tenant_id, status, stock_item_id, qty_reserved, qty_consumed, expires_at "
                    "FROM public.stock_reservations "
                    "WHERE id = CAST(:id AS uuid) "
                    "FOR UPDATE"
                ),
                {"id": str(reservation_id)},
            ).mappings().first()
            if not r:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if str(r["tenant_id"]) != str(tenant_id):
                raise HTTPException(status_code=403, detail="Reservation tenant mismatch")
            if r["status"] != "OPEN":
                raise HTTPException(status_code=409, detail="Reservation is not OPEN")
            if str(r["stock_item_id"]) != str(obj.id):
                raise HTTPException(status_code=409, detail="Reservation stock_item_id mismatch")
            if r["expires_at"] is not None:
                now = datetime.now(timezone.utc)
                if r["expires_at"] <= now:
                    raise HTTPException(status_code=409, detail="Reservation expired")

            remaining = Decimal(str(r["qty_reserved"])) - Decimal(str(r["qty_consumed"]))
            if remaining < qty:
                raise HTTPException(status_code=409, detail="Reservation remaining qty is insufficient")

            # Apply on-hand + reserved snapshot changes
            if Decimal(str(obj.qty_on_hand)) < qty:
                raise HTTPException(status_code=409, detail="Insufficient stock")
            obj.qty_on_hand = Decimal(str(obj.qty_on_hand)) - qty
            obj.qty_reserved = Decimal(str(obj.qty_reserved)) - qty

            # Consume reservation
            new_consumed = Decimal(str(r["qty_consumed"])) + qty
            new_status = "CONSUMED" if new_consumed == Decimal(str(r["qty_reserved"])) else "OPEN"
            db.execute(
                text(
                    "UPDATE public.stock_reservations "
                    "SET qty_consumed = :qc, status = :st "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"qc": new_consumed, "st": new_status, "id": str(reservation_id)},
            )
        else:
            # Issue from FREE stock only (don't steal reserved)
            free = Decimal(str(obj.qty_on_hand)) - Decimal(str(obj.qty_reserved))
            if free < qty:
                raise HTTPException(status_code=409, detail="Insufficient free stock (reserved stock exists)")
            obj.qty_on_hand = Decimal(str(obj.qty_on_hand)) - qty

    elif t in ("RECEIPT", "RETURN"):
        obj.qty_on_hand = Decimal(str(obj.qty_on_hand)) + qty

    created_by_user_id = str(getattr(auth, "sub", None) or getattr(auth, "user_id", None) or "unknown")
    created_by_username = getattr(auth, "username", None)

    try:
        stock_tx_id = db.execute(
            text(
                """
                INSERT INTO public.stock_transactions (
                    created_by_user_id, created_by_username,
                    tenant_id, transaction_type,
                    warehouse_id, part_id, stock_item_id,
                    qty, uom,
                    idempotency_key, request_hash,
                    reservation_id
                ) VALUES (
                    :created_by_user_id, :created_by_username,
                    CAST(:tenant_id AS uuid), :transaction_type,
                    CAST(:warehouse_id AS uuid), CAST(:part_id AS uuid), CAST(:stock_item_id AS uuid),
                    :qty, :uom,
                    :idempotency_key, :request_hash,
                    CAST(:reservation_id AS uuid)
                )
                RETURNING id
                """
            ),
            {
                "created_by_user_id": created_by_user_id,
                "created_by_username": created_by_username,
                "tenant_id": tenant_id,
                "transaction_type": t,
                "warehouse_id": str(loc.warehouse_id),
                "part_id": str(obj.part_id),
                "stock_item_id": str(obj.id),
                "qty": qty,
                "uom": uom,
                "idempotency_key": idem_key,
                "request_hash": None,
                "reservation_id": str(reservation_id) if reservation_id else None,
            },
        ).scalar_one()
    except IntegrityError:
        db.rollback()
        # replay response
        existing = db.execute(
            text(
                "SELECT id, stock_item_id FROM public.stock_transactions "
                "WHERE tenant_id = CAST(:tenant_id AS uuid) AND idempotency_key = :k"
            ),
            {"tenant_id": tenant_id, "k": idem_key},
        ).mappings().first()
        if existing:
            qty_on_hand = db.execute(
                text("SELECT qty_on_hand FROM public.stock_items WHERE id = CAST(:id AS uuid)"),
                {"id": str(existing["stock_item_id"])},
            ).scalar()
            return {
                "transaction_id": uuid4(),
                "stock_transaction_id": existing["id"],
                "stock_item_id": existing["stock_item_id"],
                "qty_on_hand": float(qty_on_hand) if qty_on_hand is not None else None,
            }
        raise HTTPException(status_code=409, detail="Duplicate idempotency_key")

    db.add(obj)
    db.commit()
    db.refresh(obj)

    return {
        "transaction_id": uuid4(),
        "stock_transaction_id": stock_tx_id,
        "stock_item_id": obj.id,
        "qty_on_hand": float(obj.qty_on_hand),
    }
