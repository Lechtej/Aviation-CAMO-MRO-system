from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, DateTime, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from shared.orm import Base


class DmsDocumentType(Base):
    __tablename__ = "dms_document_types"

    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    domain = Column(String(16), nullable=False)
    title = Column(String(128), nullable=False)
    requires_signature = Column(Boolean, nullable=False, default=False)
    printable = Column(Boolean, nullable=False, default=False)
    retention_years = Column(Integer, nullable=True)
    immutable_after = Column(String(16), nullable=False, default="ISSUED")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DmsDocument(Base):
    __tablename__ = "dms_documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    type_code = Column(String(64), ForeignKey("dms_document_types.code", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    status = Column(String(16), nullable=False, default="DRAFT")
    title = Column(String(255), nullable=True)
    entity_kind = Column(String(32), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    effective_at = Column(DateTime(timezone=True), nullable=True)
    created_by_sub = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_dms_documents_type_code", "type_code"),
        Index("ix_dms_documents_status", "status"),
        Index("ix_dms_documents_entity", "entity_kind", "entity_id"),
    )


class DmsAttachment(Base):
    __tablename__ = "dms_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("dms_documents.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(128), nullable=True)
    storage_key = Column(String(512), nullable=False)
    sha256 = Column(String(64), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    created_by_sub = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_dms_attachments_document_id", "document_id"),
    )


class DmsSignature(Base):
    __tablename__ = "dms_signatures"

    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("dms_documents.id", ondelete="CASCADE"), nullable=False)
    signed_by_sub = Column(String(128), nullable=False)
    signed_role = Column(String(64), nullable=False)
    signed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    signature_hash = Column(String(64), nullable=False)

    __table_args__ = (
        Index("ix_dms_signatures_document_id", "document_id"),
    )
