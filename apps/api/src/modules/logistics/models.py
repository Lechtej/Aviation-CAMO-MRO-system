from __future__ import annotations

import uuid
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.orm import Base


class PartType(str, Enum):
    ROTABLE = "ROTABLE"
    CONSUMABLE = "CONSUMABLE"
    EXPENDABLE = "EXPENDABLE"


class StockCondition(str, Enum):
    SERVICEABLE = "SERVICEABLE"
    UNSERVICEABLE = "UNSERVICEABLE"
    QUARANTINE = "QUARANTINE"


class Uom(Base):
    """Unit of Measure dictionary (shared across tenants)."""

    __tablename__ = "uom"
    __table_args__ = (
        UniqueConstraint("code", name="uq_uom_code"),
        {"schema": "shared"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(16), nullable=False)
    name = Column(String(64), nullable=False)


class Part(Base):
    __tablename__ = "parts"
    __table_args__ = (
        UniqueConstraint("part_number", name="uq_parts_part_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    part_number = Column(String(64), nullable=False)
    description = Column(String(255), nullable=True)
    part_type = Column(String(16), nullable=False)  # PartType values
    uom_code = Column(String(16), nullable=True)  # references shared.uom.code (soft ref)
    is_pool_item = Column(Boolean, nullable=False, default=False)

    stock_items = relationship("StockItem", back_populates="part")


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("code", name="uq_warehouses_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    locations = relationship("Location", back_populates="warehouse")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_locations_warehouse_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(64), nullable=False)
    name = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    warehouse = relationship("Warehouse", back_populates="locations")
    stock_items = relationship("StockItem", back_populates="location")


class StockItem(Base):
    """Represents stock state at a given location (simplified).

    - For consumables/expedables: quantity can be > 1 (non-serialized)
    - For rotables: quantity is typically 1 and serial_number is required in real life
      (kept flexible in this skeleton).
    """

    __tablename__ = "stock_items"
    __table_args__ = (
        UniqueConstraint("part_id", "location_id", "serial_number", name="uq_stock_part_loc_sn"),
        CheckConstraint("qty_on_hand >= 0", name="ck_stock_qty_on_hand_nonneg"),
        CheckConstraint("qty_reserved >= 0", name="ck_stock_qty_reserved_nonneg"),
        CheckConstraint("qty_in_transit >= 0", name="ck_stock_qty_in_transit_nonneg"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    part_id = Column(UUID(as_uuid=True), ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False)
    serial_number = Column(String(64), nullable=True)

    condition = Column(String(16), nullable=False, default=StockCondition.SERVICEABLE.value)
    owner = Column(String(128), nullable=False, default="TENANT")
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)

    qty_on_hand = Column(Numeric(14, 3), nullable=False, default=0)
    qty_reserved = Column(Numeric(14, 3), nullable=False, default=0)
    qty_in_transit = Column(Numeric(14, 3), nullable=False, default=0)

    part = relationship("Part", back_populates="stock_items")
    location = relationship("Location", back_populates="stock_items")
