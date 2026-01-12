from __future__ import annotations

from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from .models import PartType, StockCondition


class UomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class PartCreate(BaseModel):
    part_number: str = Field(min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=255)
    part_type: PartType
    uom_code: Optional[str] = Field(default=None, max_length=16)
    is_pool_item: bool = False


class PartUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=255)
    part_type: Optional[PartType] = None
    uom_code: Optional[str] = Field(default=None, max_length=16)
    is_pool_item: Optional[bool] = None


class PartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    part_number: str
    description: Optional[str] = None
    part_type: str
    uom_code: Optional[str] = None
    is_pool_item: bool


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    is_active: Optional[bool] = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    is_active: bool


class LocationCreate(BaseModel):
    warehouse_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, max_length=128)
    is_active: bool = True


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    is_active: Optional[bool] = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    warehouse_id: UUID
    code: str
    name: Optional[str] = None
    is_active: bool


class StockItemCreate(BaseModel):
    part_id: UUID
    location_id: UUID
    serial_number: Optional[str] = Field(default=None, max_length=64)
    condition: StockCondition = StockCondition.SERVICEABLE
    owner: str = Field(default="TENANT", max_length=128)
    qty_on_hand: float = Field(default=0, ge=0)
    qty_reserved: float = Field(default=0, ge=0)
    qty_in_transit: float = Field(default=0, ge=0)


class StockItemUpdate(BaseModel):
    location_id: Optional[UUID] = None
    condition: Optional[StockCondition] = None
    owner: Optional[str] = Field(default=None, max_length=128)
    qty_on_hand: Optional[float] = Field(default=None, ge=0)
    qty_reserved: Optional[float] = Field(default=None, ge=0)
    qty_in_transit: Optional[float] = Field(default=None, ge=0)


class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    part_id: UUID
    location_id: UUID
    serial_number: Optional[str] = None
    condition: str
    owner: str
    qty_on_hand: float
    qty_reserved: float
    qty_in_transit: float

class StockTransactionCreate(BaseModel):
    type: str = Field(pattern="^(RECEIPT|ISSUE|RETURN)$")
    stock_item_id: UUID
    qty: float = Field(gt=0)


class StockTransactionOut(BaseModel):
    transaction_id: UUID
    stock_item_id: UUID
    qty_on_hand: float
