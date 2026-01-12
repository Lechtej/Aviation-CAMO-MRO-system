from __future__ import annotations

from decimal import Decimal

from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.db import get_db_session
from . import models
from .schemas import (
    PartCreate, PartUpdate, PartOut,
    WarehouseCreate, WarehouseUpdate, WarehouseOut,
    LocationCreate, LocationUpdate, LocationOut,
    StockItemCreate, StockItemUpdate, StockItemOut,
    UomOut, StockTransactionCreate, StockTransactionOut,
)
from .bootstrap import bootstrap_shared_dictionaries, bootstrap_tenant_tables

router = APIRouter(prefix="/v1/logistics", tags=["Logistics"])


def require_role(request: Request, role: str) -> None:
    auth = getattr(request.state, "auth", None)
    if not auth or role not in getattr(auth, "roles", []):
        raise HTTPException(status_code=403, detail=f"Missing role: {role}")


@router.post("/_admin/bootstrap", status_code=201)
def bootstrap_logistics(request: Request, db: Session = Depends(get_db_session)):
    """Creates schemas/tables needed for Logistics (dev bootstrap).

    Notes:
    - Creates shared dictionaries (UoM) in schema `shared`
    - Creates tenant tables in the active tenant schema (via search_path)
    """
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
    # ensure warehouse exists
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
    # validate references
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


@router.post("/stock-transactions", response_model=StockTransactionOut, status_code=201)
def create_stock_transaction(payload: StockTransactionCreate, db: Session = Depends(get_db_session)):
    obj = (
        db.query(models.StockItem)
        .filter(models.StockItem.id == payload.stock_item_id)
        .with_for_update()
        .one_or_none()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="Stock item not found")

    qty = Decimal(str(payload.qty))
    t = payload.type.upper()

    if t == "ISSUE":
        if obj.qty_on_hand < qty:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        obj.qty_on_hand -= qty
    elif t in ("RECEIPT", "RETURN"):
        obj.qty_on_hand += qty
    else:
        raise HTTPException(status_code=422, detail="Invalid transaction type")

    db.add(obj)
    db.commit()
    db.refresh(obj)

    return {
        "transaction_id": uuid4(),
        "stock_item_id": obj.id,
        "qty_on_hand": float(obj.qty_on_hand),
    }
