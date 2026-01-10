# GitHub Releasing (ZIP-first)

## Scope
Canonical release procedure for **Aviation-CAMO-MRO-system** hosted on GitHub.
Goal: reproducible releases, one artifact, one tag, one changelog.

## Rules (non-negotiable)
1. **One ZIP = one release** (no multiple ZIPs per version).
2. **Single cumulative changelog**: `RELEASE_NOTES.md` (append-only; newest entry on top).
3. **Semantic versioning**: `vX.Y.Z` (early development uses `v0.x.y`).
4. **Tags must match ZIP name** (same version string).
5. No committing secrets: `.env` files are not versioned (use templates in `infra/*/env.example`).

## Canonical steps
### 1) Prepare working tree
```bash
git status --porcelain
```
- must be clean or changes are intentional for this release.

### 2) Update documentation
- Update `RELEASE_NOTES.md` with a new section: `## vX.Y.Z (YYYY-MM-DD) — <short title>`.
- If needed, update `README.md` and docs.

### 3) Create the release ZIP
- ZIP name convention:
  - `AviationCAMO-MRO_vX.Y.Z_<SHORT-TOPIC>.zip` (release package)
- ZIP must contain the repository snapshot in a single top-level folder.

### 4) Git tag
```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

### 5) GitHub Release
- Create Release for tag `vX.Y.Z`.
- Attach the ZIP artifact.
- Paste the top section from `RELEASE_NOTES.md` for that version.

## Validation checklist (before publishing)
- [ ] `docker compose up -d --build` is green
- [ ] `curl -i http://127.0.0.1:8000/health` returns 200
- [ ] `docker compose logs --tail=200 api` contains no traceback
- [ ] DB migrations run cleanly (if changed)
- [ ] `RELEASE_NOTES.md` entry exists for version


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
