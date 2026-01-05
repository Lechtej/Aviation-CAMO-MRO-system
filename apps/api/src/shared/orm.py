from __future__ import annotations

from sqlalchemy.orm import declarative_base

# Single declarative base for all SQLAlchemy ORM models in the API service.
Base = declarative_base()
