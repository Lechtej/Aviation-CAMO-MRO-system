from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.db import engine, ensure_schema
from shared.orm import Base
from .models import Uom


DEFAULT_UOMS = [
    ("EA", "Each"),
    ("PCS", "Pieces"),
    ("SET", "Set"),
    ("KG", "Kilogram"),
    ("L", "Liter"),
]


def bootstrap_shared_dictionaries(db: Session) -> None:
    """Ensure shared schema + seed minimal dictionaries."""
    ensure_schema("shared")
    # Create shared tables (UoM etc.)
    Base.metadata.create_all(bind=engine, checkfirst=True)

    existing = {row[0] for row in db.execute(select(Uom.code)).all()}
    for code, name in DEFAULT_UOMS:
        if code not in existing:
            db.add(Uom(code=code, name=name))
    db.commit()


def bootstrap_tenant_tables() -> None:
    """Create tenant-scoped tables in the active search_path schema.

    Requires tenant middleware to have set current_schema before DB checkout.
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)
