from __future__ import annotations

from decimal import Decimal

from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class AircraftStatusTech(str, Enum):
    IN_SERVICE = "IN_SERVICE"
    AOG = "AOG"
    MAINTENANCE = "MAINTENANCE"
    STORED = "STORED"


class AircraftCreate(BaseModel):
    registration: str = Field(min_length=1, max_length=32)
    aircraft_type: Optional[str] = Field(default=None, max_length=64)
    serial_number: Optional[str] = Field(default=None, max_length=64)
    status_tech: AircraftStatusTech = AircraftStatusTech.IN_SERVICE
    notes: Optional[str] = Field(default=None, max_length=1024)


class AircraftUpdateOwner(BaseModel):
    """Full update allowed for aircraft owner."""

    registration: Optional[str] = Field(default=None, max_length=32)
    aircraft_type: Optional[str] = Field(default=None, max_length=64)
    serial_number: Optional[str] = Field(default=None, max_length=64)
    status_tech: Optional[AircraftStatusTech] = None
    notes: Optional[str] = Field(default=None, max_length=1024)


class AircraftUpdateMro(BaseModel):
    """Limited update allowed for MRO tenants (scope B)."""

    status_tech: Optional[AircraftStatusTech] = None
    notes: Optional[str] = Field(default=None, max_length=1024)


class AircraftOut(BaseModel):
    id: UUID
    owner_tenant_id: UUID
    registration: str
    aircraft_type: Optional[str]
    serial_number: Optional[str]
    status_tech: str
    notes: Optional[str]

    manufacture_date: Optional[date] = None
    entry_into_service_date: Optional[date] = None

    total_fh: Optional[Decimal] = None
    total_fc: Optional[int] = None

    class Config:
        from_attributes = True


class MroAccessCreate(BaseModel):
    mro_tenant_id: UUID
    role: str = Field(default="MRO_EDITOR", min_length=1, max_length=32)
    active: bool = True


class MroAccessOut(BaseModel):
    id: UUID
    aircraft_id: UUID
    mro_tenant_id: UUID
    role: str
    active: bool

    class Config:
        from_attributes = True


class AircraftWithMroAccessOut(AircraftOut):
    mro_access: List[MroAccessOut] = []


class MaintenanceStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class AircraftMaintenanceEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    status: MaintenanceStatus = MaintenanceStatus.OPEN


class AircraftMaintenanceEventUpdate(BaseModel):
    """Update schema.

    NOTE: Actual allowed fields depend on caller type:
    - Owner: may update all fields
    - MRO: may update only status + mro_notes
    """

    title: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = None
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    status: Optional[MaintenanceStatus] = None
    mro_notes: Optional[str] = None


class AircraftMaintenanceEventOut(BaseModel):
    id: UUID
    aircraft_id: UUID
    created_by_tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    title: str
    description: Optional[str]
    planned_start_at: Optional[datetime]
    planned_end_at: Optional[datetime]
    status: str
    mro_notes: Optional[str]

    class Config:
        from_attributes = True


class AircraftUtilizationIn(BaseModel):
    op_date: date
    delta_fh: Decimal = Field(ge=0)
    delta_fc: int = Field(ge=0)
    source: str = Field(default="MANUAL", max_length=32)
    source_ref: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=1024)


class AircraftUtilizationOut(AircraftUtilizationIn):
    id: UUID
    aircraft_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AircraftCountersOut(BaseModel):
    aircraft_id: UUID
    total_fh: Decimal
    total_fc: int
    updated_at: datetime

    class Config:
        from_attributes = True
