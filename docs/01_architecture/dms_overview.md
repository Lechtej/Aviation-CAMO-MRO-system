# DMS — Document Management System (CAMO/MRO)

## 1. Scope
DMS is a **core subsystem** of the platform (not an "attachments" feature). It manages **regulatory documents** across CAMO, MRO and STORES with:
- explicit document types,
- lifecycle/workflow,
- signatures (role-aware),
- print outputs (PDF/tags),
- immutable archive + audit trail.

**Key rule:** *Document ≠ file.* A file (PDF/JPG) is an artifact attached to a document instance.

## 2. Document model
### 2.1 Document Type Registry (static)
A controlled registry (seeded, versioned) defining compliance rules per document type.

Minimum fields:
- `code` (e.g. `EASA_FORM_1`, `WORK_ORDER`, `CRS_145`)
- `domain` (`CAMO` | `MRO` | `STORES`)
- `requires_signature` (bool)
- `allowed_roles` (RBAC roles that can approve/issue/sign)
- `printable` (bool)
- `retention_policy` (e.g. `YEARS:3`, `LIFETIME`)
- `immutable_after` (`ISSUED` | `SIGNED`)

### 2.2 Document Instance (dynamic)
A runtime object with:
- `status` (lifecycle),
- `metadata` (typed fields per document type),
- `links` (aircraft / WO / part / serial / reservation / ledger),
- `artifacts` (PDF render, uploads),
- `signatures`.

## 3. Lifecycle
Baseline lifecycle (MVP):

```
DRAFT
 → REVIEW (optional)
 → APPROVED
 → ISSUED
 → SIGNED (if required)
 → ARCHIVED (immutable)
```

Constraints:
- No deletion (append-only). Superseding is allowed (new version references previous).
- No edits after `immutable_after` threshold.
- Every state transition must be audited.

## 4. Signatures (MVP)
MVP signature is **internal** (system-recorded):
- `user_id`, `role`, `timestamp`, `document_hash`, optional `comment`.

Signature enforcement:
- allowed roles derive from Document Type Registry,
- signature can be required at `ISSUED` or `SIGNED` depending on document type.

## 5. Storage
- Attachments stored in a dedicated storage backend (dev: filesystem volume, target: S3/MinIO).
- Each stored object must have `sha256` hash.
- Archived documents must be reproducible (render PDF deterministically from metadata + template version).

## 6. Printing / tags
MVP outputs:
- PDF render from templates (document-type specific).
- Tags (serviceable / unserviceable / quarantine) with QR that resolves to read-only document view.

## 7. MVP Document types
### CAMO
- `AMP_REV` (maintenance program revision)
- `AD_STATUS`
- `SB_STATUS`
- `ARC`
- `CRS_CAMO`

### MRO
- `WORK_ORDER`
- `TASK_CARD`
- `JOB_CARD`
- `CRS_145`
- `RTS_PACKAGE`

### STORES
- `EASA_FORM_1` (structured record + PDF)
- `CERTIFICATE_OF_CONFORMANCE`
- `QUARANTINE_TAG`
- `SERVICEABLE_TAG`

## 8. UI (module)
DMS requires its own UI module with:
- Documents list (filters: type/status/domain/entity)
- Document details (timeline, metadata, attachments, signatures)
- Lifecycle actions (Approve/Issue/Sign/Archive)
- Print/Render actions

