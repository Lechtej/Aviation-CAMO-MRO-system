# API — DMS (Draft Contract)

> This is a draft contract for the DMS module. It defines MVP endpoints and invariants.

## Principles
- Every call is tenant-scoped.
- Documents are append-only; no hard delete.
- Lifecycle transitions are validated and audited.

## Endpoints (v1)
### Types
- `GET /v1/dms/types` — list document types (registry)

### Documents
- `GET /v1/dms/documents` — list (filters: type/status/domain/related entity)
- `POST /v1/dms/documents` — create DRAFT
- `GET /v1/dms/documents/{id}` — details
- `PATCH /v1/dms/documents/{id}` — update metadata (only when editable)

### Lifecycle
- `POST /v1/dms/documents/{id}/approve`
- `POST /v1/dms/documents/{id}/issue`
- `POST /v1/dms/documents/{id}/sign`
- `POST /v1/dms/documents/{id}/archive`

### Attachments
- `POST /v1/dms/documents/{id}/attachments` — upload
- `GET /v1/dms/attachments/{id}` — download (RBAC + tenant)

### Rendering / printing
- `POST /v1/dms/documents/{id}/render` — generate PDF artifact (template-versioned)
- `GET /v1/dms/documents/{id}/pdf` — fetch latest rendered PDF

## Core invariants
- `immutable_after` enforced per type.
- Archived documents are immutable and reproducible.
- Every lifecycle transition is persisted as an audit event.

