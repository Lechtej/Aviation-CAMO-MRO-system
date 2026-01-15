from __future__ import annotations

from hashlib import sha256
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.db import get_db_session
from . import models
from .schemas import (
    DocumentTypeCreate,
    DocumentTypeOut,
    DocumentCreate,
    DocumentOut,
    LifecycleAction,
)

router = APIRouter(prefix="/v1/dms", tags=["DMS"])


def _require_tenant(request: Request) -> None:
    tenant = getattr(request.state, "tenant", None)
    if not tenant or not getattr(tenant, "tenant_id", None):
        raise HTTPException(status_code=403, detail="Tenant context missing")


def _sub(request: Request) -> Optional[str]:
    auth = getattr(request.state, "auth", None)
    if not auth:
        return None
    # Prefer OIDC 'sub' claim when present.
    sub = auth.claims.get("sub") if getattr(auth, "claims", None) else None
    if isinstance(sub, str) and sub:
        return sub
    return None


@router.get("/types", response_model=List[DocumentTypeOut])
def list_types(request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    return db.query(models.DmsDocumentType).order_by(models.DmsDocumentType.code.asc()).all()


@router.post("/types", response_model=DocumentTypeOut, status_code=201)
def create_type(payload: DocumentTypeCreate, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    # MVP: bootstrap types via API (later: seed-only + PLATFORM_ADMIN)
    obj = models.DmsDocumentType(
        id=uuid4(),
        code=payload.code,
        domain=str(payload.domain),
        title=payload.title,
        requires_signature=payload.requires_signature,
        printable=payload.printable,
        retention_years=payload.retention_years,
        immutable_after=payload.immutable_after,
    )
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Document type already exists (code must be unique)")
    db.refresh(obj)
    return obj


@router.get("/documents", response_model=List[DocumentOut])
def list_documents(
    request: Request,
    db: Session = Depends(get_db_session),
    type_code: Optional[str] = None,
    status: Optional[str] = None,
):
    _require_tenant(request)
    q = db.query(models.DmsDocument)
    if type_code:
        q = q.filter(models.DmsDocument.type_code == type_code)
    if status:
        q = q.filter(models.DmsDocument.status == status)
    return q.order_by(models.DmsDocument.created_at.desc()).all()


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(payload: DocumentCreate, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    # Validate type exists
    t = db.query(models.DmsDocumentType).filter(models.DmsDocumentType.code == payload.type_code).first()
    if not t:
        raise HTTPException(status_code=400, detail="Unknown document type_code")

    obj = models.DmsDocument(
        id=uuid4(),
        type_code=payload.type_code,
        status="DRAFT",
        title=payload.title,
        entity_kind=str(payload.entity_kind) if payload.entity_kind else None,
        entity_id=payload.entity_id,
        effective_at=payload.effective_at,
        created_by_sub=_sub(request),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return obj


def _transition(db: Session, obj: models.DmsDocument, to_status: str) -> models.DmsDocument:
    allowed = {
        "DRAFT": {"REVIEW", "APPROVED"},
        "REVIEW": {"APPROVED"},
        "APPROVED": {"ISSUED"},
        "ISSUED": {"SIGNED", "ARCHIVED"},
        "SIGNED": {"ARCHIVED"},
        "ARCHIVED": set(),
    }
    if to_status not in allowed.get(obj.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid transition: {obj.status} -> {to_status}")

    obj.status = to_status
    if to_status == "ISSUED":
        obj.issued_at = func_now(db)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def func_now(db: Session):
    # Use DB 'now()' for audit-consistent timestamps
    return db.execute(text("SELECT now()::timestamptz")).scalar()


@router.post("/documents/{document_id}/review", response_model=DocumentOut)
def to_review(document_id: UUID, _: LifecycleAction, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return _transition(db, obj, "REVIEW")


@router.post("/documents/{document_id}/approve", response_model=DocumentOut)
def approve(document_id: UUID, _: LifecycleAction, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return _transition(db, obj, "APPROVED")


@router.post("/documents/{document_id}/issue", response_model=DocumentOut)
def issue(document_id: UUID, _: LifecycleAction, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return _transition(db, obj, "ISSUED")


@router.post("/documents/{document_id}/sign", response_model=DocumentOut)
def sign(document_id: UUID, payload: LifecycleAction, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)

    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")

    # Ensure type requires signature
    t = db.query(models.DmsDocumentType).filter(models.DmsDocumentType.code == obj.type_code).first()
    if not t:
        raise HTTPException(status_code=500, detail="Document type missing")
    if not t.requires_signature:
        raise HTTPException(status_code=409, detail="Document type does not require signature")

    # Determine role (MVP: first role in token). Later: enforce allowed_roles per type.
    auth = getattr(request.state, "auth", None)
    roles = getattr(auth, "roles", []) if auth else []
    if not roles:
        raise HTTPException(status_code=403, detail="No roles in auth context")

    if obj.status != "ISSUED":
        raise HTTPException(status_code=409, detail="Document must be ISSUED before SIGN")

    role = str(roles[0])
    sub = _sub(request) or "unknown"

    # Signature hash = sha256(document_id + status + role + sub + note)
    raw = f"{obj.id}|{obj.status}|{role}|{sub}|{payload.note or ''}".encode("utf-8")
    sig_hash = sha256(raw).hexdigest()

    sig = models.DmsSignature(
        id=uuid4(),
        document_id=obj.id,
        signed_by_sub=sub,
        signed_role=role,
        signature_hash=sig_hash,
    )
    db.add(sig)

    obj.status = "SIGNED"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/documents/{document_id}/archive", response_model=DocumentOut)
def archive(document_id: UUID, _: LifecycleAction, request: Request, db: Session = Depends(get_db_session)):
    _require_tenant(request)
    obj = db.query(models.DmsDocument).filter(models.DmsDocument.id == document_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Document not found")
    return _transition(db, obj, "ARCHIVED")
