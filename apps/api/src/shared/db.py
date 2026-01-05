from __future__ import annotations

"""Database plumbing (v0.2.2)

Implements schema-per-tenant routing via PostgreSQL search_path.

Mechanism:
- Middleware resolves TenantContext and sets current schema in a ContextVar
- SQLAlchemy engine uses a checkout listener to apply SET search_path per connection

Note:
- This is plumbing-only; models/migrations will follow in later versions.
"""

import os
from contextvars import ContextVar
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://aviation:aviation@db:5432/aviation")

current_schema: ContextVar[str] = ContextVar("current_schema", default="public")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

@event.listens_for(engine, "checkout")
def _set_search_path(dbapi_conn, conn_record, conn_proxy):
    schema = current_schema.get()
    # Always include shared schema second to allow global dictionaries later.
    search_path = f"{schema}, shared, public"
    cur = dbapi_conn.cursor()
    cur.execute(f"SET search_path TO {search_path}")
    cur.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db_session() -> Session:
    return SessionLocal()
