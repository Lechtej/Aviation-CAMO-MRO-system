from __future__ import annotations

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    code: str = Field(
        ..., min_length=2, max_length=32,
        description="Human-friendly tenant code (e.g. 'acme'). Allowed: a-z, 0-9, underscore; must start with letter."
    )
    name: str = Field(..., min_length=2, max_length=128, description="Tenant display name")


class TenantOut(BaseModel):
    id: str
    code: str
    name: str
    schema_name: str
    status: str
    created_at: str
