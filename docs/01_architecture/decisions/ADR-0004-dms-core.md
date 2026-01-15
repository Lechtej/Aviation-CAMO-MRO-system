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

