# ADR-0004 — DMS as Core Subsystem (Document ≠ Attachment)

**Status:** Accepted

## Context
CAMO/MRO operations are compliance-driven. Regulatory artifacts (EASA Form 1, CRS, task cards, AMP revisions, tags) cannot be treated as free-form file uploads without:
- type control,
- lifecycle enforcement,
- signature enforcement,
- immutable archiving,
- traceable links to aircraft/WO/parts.

## Decision
Introduce **DMS as a core subsystem** with:
1) Document Type Registry (seeded, controlled)
2) Document Instance model (typed metadata + links + artifacts)
3) Lifecycle state machine (audit on every transition)
4) Internal signatures (MVP) + future external qualified signatures
5) Deterministic render/print outputs (PDF/tags)
6) Immutable archive (hash + retention policy)

**Rule:** Document is a domain object. Attachments are secondary artifacts bound to a document instance.

## Consequences
- Backend requires dedicated tables and API endpoints.
- UI requires a dedicated DMS module (list/details/actions/print).
- Data retention and immutability become enforceable.

## Risks / mitigations
- **Risk:** users attempt to upload scans without context → **Mitigation:** enforce entity links and document type.
- **Risk:** PDF-only Form 1 → **Mitigation:** Form 1 is stored as structured record + generated PDF.
- **Risk:** edits after CRS → **Mitigation:** immutable_after threshold + snapshot hash.



---

## ADDENDUM 2026-01-16 — DMS review pass (docs hardening)

### Addendum: tenancy + storage abstraction
Additional constraints adopted for implementation stability:
- **Tenant-scoped documents**: every document instance and artifact is scoped to a tenant schema; cross-tenant access is forbidden by default.
- **No binary blobs in PostgreSQL**: DB stores metadata + hashes + logical storage keys; binary content lives in a storage backend.
- **Storage abstraction**: implementation must support `filesystem` (DEV) and `S3/MinIO` (target) without changing DB schema.
- **Version chain**: superseding a document creates a new document version referencing `supersedes_document_id` (append-only history).

### Consequences (extended)
- DB requires tenant migration(s) for DMS tables (see `db/migrations/tenant/0002_dms.sql`).
- API must enforce tenant context before any DMS handler executes.
- Artifact download endpoints must enforce both RBAC and tenant isolation.
