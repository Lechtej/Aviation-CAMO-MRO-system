# PATCH — DMS Documentation Update (v0.2.47)

## Purpose
This patch introduces **DMS (Document Management System)** as a **core subsystem** in Aviation CAMO/MRO and updates existing documentation **additively** (append-only policy preserved).

## What is included
Updated / new documentation files:
- `README.md` — new DMS addendum + links
- `RELEASE_NOTES.md` — new entry for DMS baseline (docs)
- `docs/master/AVIATION_CAMO_MRO_MASTER_DOC.md` — DEC-010 + DMS addendum
- `docs/00_product/wbs.md` — WBS extended with DMS module
- `docs/01_architecture/wbs_modules.md` — Platform milestone extended with DMS
- `docs/01_architecture/dms_overview.md` — DMS architecture baseline
- `docs/01_architecture/decisions/ADR-0004-dms-core.md` — formal decision record
- `docs/02_api/dms.md` — draft API contract (docs only)

## How to apply
1. Unzip this patch **over repository root** (preserve paths).
2. Verify that updated files are present in the exact paths listed above.

## Notes
- Patch is documentation-only (no code, no migrations).
- The DMS API described in `docs/02_api/dms.md` is a **contract draft** for the next implementation iteration.

## Patch: DMS DOCS v0.2.49 (additive)
- Extended DMS overview with regulatory baseline (CAMO/MRO/STORES) and print/tag outputs.
- Extended DMS API doc with OIDC/JWKS runtime requirements + troubleshooting.
- Added DEV Keycloak realm persistence ops note.
- Added README addendum + release notes entry.

## v0.2.49 — DMS docs + DEV auth/keycloak ops
- Extended DMS overview with regulatory baseline (CAMO/MRO/STORES) and required artifacts.
- Extended DMS API doc with OIDC issuer/JWKS troubleshooting.
- Added DEV ops guide for Keycloak realm persistence.
