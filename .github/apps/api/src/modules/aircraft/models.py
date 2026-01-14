from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    String,
    UniqueConstraint,
    CheckConstraint,
    DateTime,
    Date,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.orm import Base


class AircraftStatusTech(str, Enum):
    IN_SERVICE = "IN_SERVICE"
    AOG = "AOG"  # Aircraft On Ground
    MAINTENANCE = "MAINTENANCE"
    STORED = "STORED"


class Aircraft(Base):
    """Global aircraft registry.

    Business rules:
    - One owner tenant (airline) => owner_tenant_id
    - Many MRO tenants can get service access via AircraftMroAccess

    Stored in public schema intentionally (shared across tenants).
    """

    __tablename__ = "aircraft"
    __table_args__ = (
        UniqueConstraint("owner_tenant_id", "registration", name="uq_aircraft_owner_registration"),
        CheckConstraint(
            "status_tech IN ('IN_SERVICE','AOG','MAINTENANCE','STORED')",
            name="ck_aircraft_status_tech",
        ),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_tenant_id = Column(UUID(as_uuid=True), nullable=False)

    registration = Column(String(32), nullable=False)
    aircraft_type = Column(String(64), nullable=True)
    serial_number = Column(String(64), nullable=True)

    manufacture_date = Column(Date, nullable=True)
    entry_into_service_date = Column(Date, nullable=True)

    status_tech = Column(String(16), nullable=False, default=AircraftStatusTech.IN_SERVICE.value)
    notes = Column(String(1024), nullable=True)

    mro_access = relationship("AircraftMroAccess", back_populates="aircraft", cascade="all, delete-orphan")
    maintenance_events = relationship(
        "AircraftMaintenanceEvent",
        back_populates="aircraft",
        cascade="all, delete-orphan",
    )


class AircraftMroAccess(Base):
    """Service access relation: which MRO tenant can work on which aircraft."""

    __tablename__ = "aircraft_mro_access"
    __table_args__ = (
        UniqueConstraint("aircraft_id", "mro_tenant_id", name="uq_aircraft_mro_access"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aircraft_id = Column(UUID(as_uuid=True), ForeignKey("public.aircraft.id", ondelete="CASCADE"), nullable=False)
    mro_tenant_id = Column(UUID(as_uuid=True), nullable=False)

    role = Column(String(32), nullable=False, default="MRO_EDITOR")
    active = Column(Boolean, nullable=False, default=True)

    aircraft = relationship("Aircraft", back_populates="mro_access")


class AircraftMaintenanceEvent(Base):
    """Maintenance events for an aircraft.

    Stored in PUBLIC schema because multiple tenants can access the same aircraft
    (owner + assigned MROs).
    """

    __tablename__ = "aircraft_maintenance_events"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','IN_PROGRESS','DONE','CANCELLED')", name="chk_aircraft_maint_status"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aircraft_id = Column(UUID(as_uuid=True), ForeignKey("public.aircraft.id", ondelete="CASCADE"), nullable=False)

    created_by_tenant_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    title = Column(String(128), nullable=False)
    # Optional discriminator used by the global /v1/maintenance-events endpoints.
    # Kept nullable for backward compatibility with earlier versions.
    event_type = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    planned_start_at = Column(DateTime(timezone=True), nullable=True)
    planned_end_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(16), nullable=False, server_default="OPEN")
    mro_notes = Column(Text, nullable=True)

    aircraft = relationship("Aircraft", back_populates="maintenance_events")


class AircraftUtilizationSource(str, Enum):
    MANUAL = "MANUAL"
    FLIGHT_LOG = "FLIGHT_LOG"
    IMPORT = "IMPORT"


class AircraftUtilizationLedger(Base):
    __tablename__ = "aircraft_utilization_ledger"
    __table_args__ = (
        CheckConstraint("delta_fh >= 0 AND delta_fc >= 0", name="ck_aircraft_util_delta_nonneg"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    aircraft_id = Column(UUID(as_uuid=True), ForeignKey("public.aircraft.id", ondelete="CASCADE"), nullable=False)
    op_date = Column(Date, nullable=False)

    delta_fh = Column(Numeric(10, 2), nullable=False, default=0)
    delta_fc = Column(Integer, nullable=False, default=0)

    source = Column(String(32), nullable=False, default=AircraftUtilizationSource.MANUAL.value)
    source_ref = Column(String(128), nullable=True)
    notes = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    aircraft = relationship("Aircraft")


class AircraftCounters(Base):
    __tablename__ = "aircraft_counters"
    __table_args__ = (
        CheckConstraint("total_fh >= 0 AND total_fc >= 0", name="ck_aircraft_counters_nonneg"),
        {"schema": "public"},
    )

    aircraft_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.aircraft.id", ondelete="CASCADE"),
        primary_key=True,
    )

    total_fh = Column(Numeric(12, 2), nullable=False, default=0)
    total_fc = Column(Integer, nullable=False, default=0)

    last_ledger_id = Column(UUID(as_uuid=True), ForeignKey("public.aircraft_utilization_ledger.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    aircraft = relationship("Aircraft")
