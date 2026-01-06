from __future__ import annotations

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
