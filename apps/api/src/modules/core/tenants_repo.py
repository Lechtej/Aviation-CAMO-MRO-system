from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from shared.db import engine, current_schema, ensure_schema
from modules.logistics.bootstrap import bootstrap_tenant_tables


TENANT_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


def ensure_public_tables() -> None:
    """Ensure core tables exist in schema `public`.

    We keep this independent from ORM Base.metadata to avoid accidentally
    creating tenant-scoped tables in `public`.
    """
    with engine.begin() as conn:
        conn.execute(text('CREATE SCHEMA IF NOT EXISTS "public"'))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.tenants (
                    id uuid PRIMARY KEY,
                    code text NOT NULL UNIQUE,
                    name text NOT NULL,
                    schema_name text NOT NULL UNIQUE,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )


def normalize_tenant_code(code: str) -> str:
    c = (code or "").strip().lower()
    if not TENANT_CODE_RE.match(c):
        raise ValueError(
            "Invalid tenant code. Allowed: a-z, 0-9, underscore; must start with letter; length 2-32."
        )
    return c


def create_tenant(*, code: str, name: str) -> dict:
    ensure_public_tables()

    t_id = uuid.uuid4()
    c = normalize_tenant_code(code)
    schema_name = f"tenant_{c}"

    # 1) insert tenant record (public)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO public.tenants (id, code, name, schema_name)
                    VALUES (:id, :code, :name, :schema_name)
                    """
                ),
                {"id": str(t_id), "code": c, "name": name.strip(), "schema_name": schema_name},
            )
    except IntegrityError as e:
        # code/schema_name unique
        raise

    # 2) create tenant schema and run minimal migrations in that schema
    ensure_schema(schema_name)
    token = current_schema.set(schema_name)
    try:
        bootstrap_tenant_tables()
    finally:
        current_schema.reset(token)

    # 3) fetch created_at for response
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, code, name, schema_name, created_at FROM public.tenants WHERE id = :id"),
            {"id": str(t_id)},
        ).mappings().first()

    created_at = row["created_at"]
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    return {
        "id": str(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "schema_name": row["schema_name"],
        "status": "ACTIVE",
        "created_at": created_at,
    }


def list_tenants() -> list[dict]:
    ensure_public_tables()
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, code, name, schema_name, created_at FROM public.tenants ORDER BY created_at DESC")
        ).mappings().all()

    out: list[dict] = []
    for r in rows:
        created_at = r["created_at"]
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        out.append(
            {
                "id": str(r["id"]),
                "code": r["code"],
                "name": r["name"],
                "schema_name": r["schema_name"],
                "status": "ACTIVE",
                "created_at": created_at,
            }
        )
    return out


def get_schema_name_for_tenant_id(tenant_id: str) -> str | None:
    """Lookup schema_name in public.tenants.

    Returns None when tenant_id is unknown.
    """
    ensure_public_tables()
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT schema_name FROM public.tenants WHERE id = :id"),
            {"id": tenant_id},
        ).mappings().first()
    return None if not row else str(row["schema_name"])
