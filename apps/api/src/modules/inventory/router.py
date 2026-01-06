from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.db import get_db_session
from modules.logistics import models
from modules.logistics.schemas import PartCreate, PartUpdate, PartOut


router = APIRouter(prefix="/v1/inventory", tags=["Inventory"])


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
