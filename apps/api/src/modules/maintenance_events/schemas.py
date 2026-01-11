from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MaintenanceEventStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class MaintenanceEventCreate(BaseModel):
    aircraft_id: UUID
    event_type: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=5000)


class MaintenanceEventUpdate(BaseModel):
    """MRO update payload (v0).

    Only status + mro_notes are mutable in EPIC2 runtime.
    """

    status: MaintenanceEventStatus
    mro_notes: Optional[str] = Field(None, max_length=5000)


class MaintenanceEventOut(BaseModel):
    id: UUID
    aircraft_id: UUID
    tenant_id: UUID
    event_type: Optional[str] = None
    description: Optional[str] = None
    status: MaintenanceEventStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    mro_notes: Optional[str] = None

    class Config:
        from_attributes = True
