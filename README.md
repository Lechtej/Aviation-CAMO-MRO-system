# Aviation CAMO & MRO Platform (Foundation)

**Version:** v0.2.2 (ZIP snapshot)

This repository is a *foundation skeleton* for a multi-tenant CAMO + MRO + Logistics SaaS platform.
No business logic is implemented yet; the goal is to provide structure, documentation, and a runnable scaffold.

Staging używa overlay: `infra/staging/docker-compose.staging.yml`.

## Documentation (start here)
- Master (overview + spis treści): `docs/master/AVIATION_CAMO_MRO_MASTER_DOC.md`
- OPS / Production server access & deployment: `docs/03_ops/SERVER_AND_DEPLOYMENT.md`
- PO (non-technical) production workflow summary: `docs/00_product/PO_PROD_WORKFLOW.md`
- Architecture overview + ADR: `docs/01_architecture/architecture_overview.md`

## ENV
- Realne pliki `.env` nie są commitowane.
- Szablony ENV znajdują się w:
  - `infra/local/env.example`
  - `infra/staging/env.example`
  - `infra/prod/env.example`

## Quick start (Local / Windows)
1. Install Docker Desktop
2. From repository root run:
   - `start_and_test.bat`

## Staging / Production start (Linux)
System uruchamiany jednym, docelowym entrypointem:

```bash
bash scripts/start_system.sh
```
