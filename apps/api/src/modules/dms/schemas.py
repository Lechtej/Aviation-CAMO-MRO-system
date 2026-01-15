from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


DmsDomain = Literal["CAMO", "MRO", "STORES"]
DmsStatus = Literal["DRAFT", "REVIEW", "APPROVED", "ISSUED", "SIGNED", "ARCHIVED"]
EntityKind = Literal["AIRCRAFT", "WORK_ORDER", "PART", "OTHER"]


class DocumentTypeCreate(BaseModel):
    code: str = Field(..., max_length=64)
    domain: DmsDomain
    title: str = Field(..., max_length=128)
    requires_signature: bool = False
    printable: bool = False
    retention_years: Optional[int] = None
    immutable_after: Literal["ISSUED", "SIGNED"] = "ISSUED"


class DocumentTypeOut(BaseModel):
    id: UUID
    code: str
    domain: DmsDomain
    title: str
    requires_signature: bool
    printable: bool
    retention_years: Optional[int]
    immutable_after: Literal["ISSUED", "SIGNED"]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    type_code: str = Field(..., max_length=64)
    title: Optional[str] = Field(None, max_length=255)
    entity_kind: Optional[EntityKind] = None
    entity_id: Optional[UUID] = None
    effective_at: Optional[datetime] = None


class DocumentOut(BaseModel):
    id: UUID
    type_code: str
    status: DmsStatus
    title: Optional[str]
    entity_kind: Optional[str]
    entity_id: Optional[UUID]
    issued_at: Optional[datetime]
    effective_at: Optional[datetime]
    created_by_sub: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LifecycleAction(BaseModel):
    note: Optional[str] = Field(None, max_length=512)
