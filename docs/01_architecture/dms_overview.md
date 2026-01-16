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


## 9. Regulatory baseline — what we must support (CAMO / MRO / STORES)
This section defines a **minimum, implementation-oriented** baseline for aviation compliance documentation.
It is intentionally scoped to **what the system must handle**, not to a full regulatory interpretation.

### 9.1 CAMO (continuing airworthiness)
Minimum document families to support:
- **AMP / Maintenance Program** revisions (`AMP_REV`) + controlled distribution.
- **AD / SB status** tracking snapshots (`AD_STATUS`, `SB_STATUS`) with evidence artifacts.
- **ARC / Airworthiness Review** package (`ARC`) incl. supporting docs.
- **Reliability / utilization** periodic reports (`UTIL_REPORT`) if required by operator.

Outputs:
- PDF packages for audits.
- Read-only archive with traceable version chain.

### 9.2 MRO (Part-145 / maintenance execution)
Minimum document families to support:
- **Work order pack** (`WORK_ORDER`, `JOB_CARD`, `TASK_CARD`) with revision history.
- **CRS / Release to Service** (`CRS_145`) with signature constraints.
- **Inspection records / findings** (`INSPECTION_REPORT`) as structured + attachments.

Outputs:
- Print-ready packs (PDF) for shop-floor / audit.
- Controlled sign-off steps (internal signatures MVP).

### 9.3 STORES / Logistics (parts & traceability)
Minimum document families to support:
- **EASA Form 1** (`EASA_FORM_1`) as structured record + rendered PDF.
- **CoC / supplier certificates** (`CERTIFICATE_OF_CONFORMANCE`).
- **Quarantine / serviceability tags** (`QUARANTINE_TAG`, `SERVICEABLE_TAG`) with QR.

Outputs:
- Tag printouts (label templates) tied to stock item / serial / batch.
- Ability to re-print deterministically from stored metadata + template version.

### 9.4 Cross-cutting constraints
- Every document must be linkable to at least one entity: `Aircraft` / `Work Order` / `Part` / `Stock Item` / `Maintenance Event`.
- Lifecycle + immutability must reflect document type rules (no silent edits after issue/sign).
- Storage is pluggable: dev filesystem → target S3/MinIO.


---

## ADDENDUM 2026-01-16 — DMS review pass (docs hardening)

### 9.5 Source document vs Generated artifact (hard distinction)
**Goal:** avoid mixing *evidence* (uploaded scan) with *system output* (rendered pack/tag).

Definitions:
- **Source document**: externally produced file (scan/PDF/JPG) uploaded as evidence (e.g. supplier CoC scan).
- **Generated artifact**: system-produced output rendered from structured metadata + template version (e.g. EASA Form 1 PDF render, WO pack PDF, tags).

Rules (MVP):
1. A `DocumentInstance` may contain **both** types of artifacts, but each artifact must carry `artifact_kind` = `SOURCE` or `GENERATED`.
2. `GENERATED` artifacts are **reproducible**: same `(document_id, template_version)` => identical PDF bytes and `sha256`.
3. `SOURCE` artifacts are **never mutated**; replacement creates a new artifact row (append-only).
4. Lifecycle immutability (`immutable_after`) applies to document metadata and to adding/removing artifacts.

Operational consequences:
- Audit exports (PDF packs) must reference exact artifact ids + hashes.
- Printouts/tags should **always** be `GENERATED` so they can be re-printed deterministically.


### 9.6 Link model (entity bindings)

A document must be linkable to at least one domain entity.
MVP link keys (at least one required):
- `aircraft_id` (MSN context)
- `work_order_id` / `task_id` / `maintenance_event_id`
- `part_id` + (`serial_id` or `batch_id`)

Rule: the API must reject creation of a document that has **no link** to an entity unless the type explicitly allows `UNBOUND` (rare; admin-only).
