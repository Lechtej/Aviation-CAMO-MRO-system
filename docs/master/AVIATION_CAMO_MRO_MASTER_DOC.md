# AVIATION CAMO & MRO PLATFORM — MASTER DOCUMENT

**Version:** v0.1.1 (Documentation Update)  
**Status:** Approved baseline  
**Date:** 2026-01-05

**Runtime Baseline:** v0.2.2 (Docker Compose verified target)  

---

## 0. Document Control

### 0.1 Purpose
Single source of truth for product vision, scope, architecture, decisions, and roadmap.

### 0.2 Change Policy
- Append-only with controlled edits.
- Approved decisions are frozen in Key Decisions.
- Detailed technical artifacts live under `/docs`.

---

## 1. Vision & Scope

### 1.1 Vision
Build a modern, browser-based, multi-tenant CAMO & MRO system for small and mid-size airlines, providing audit-ready control of continuing airworthiness, maintenance execution, and logistics, with future expansion to ATL/ELB.

### 1.2 MVP Scope
- CAMO Core (fleet, AMP, due list)
- MRO Core (work orders, execution, sign-off)
- Shared Logistics (rotables, pool, consumables)
- Costing and ERP bridge (export)
- Multi-tenant SaaS foundation

### 1.3 Out of MVP (Planned)
- ATL / ELB (offline-first)
- Reliability & analytics
- Purchasing workflows (PR/PO)
- Warranty & claims

---

## 2. Key Decisions (Frozen)

- DEC-001: Multi-tenant SaaS
- DEC-002: PostgreSQL schema-per-tenant
- DEC-003: MVP = CAMO + MRO before ATL
- DEC-004: Shared Logistics module (CAMO + MRO)
- DEC-005: Monorepo
- DEC-006: One RELEASE_NOTES.md (continuously updated)
- DEC-007: Stack = FastAPI, PostgreSQL, Redis/Celery, Keycloak, React/TypeScript
- DEC-008: Tenant routing via PostgreSQL schema-per-tenant using search_path (middleware-driven context)
- DEC-009: Tenant Feature Flags per tenant (DB source of truth) + API enforcement (403 FEATURE_DISABLED)
- DEC-010: DMS as core subsystem (Document ≠ attachment; lifecycle + signatures + immutable archive)

---

## 3. WBS (See: docs/00_product/wbs.md)


## 4. RBAC (See: docs/00_product/rbac_matrix.md)

## 5. Logical Architecture

### 5.0 API Contract
- OpenAPI: `docs/02_api/openapi.yaml` (v0.2.0 contract baseline)

## 5. Logical Architecture
See diagrams in this document and detailed notes in `docs/01_architecture/architecture_overview.md`.

### 5.1 Logical Architecture (Mermaid)

```mermaid
flowchart TB
  subgraph UI[Web UI]
    WEB[React + TypeScript]
  end

  subgraph IDP[Identity Provider]
    KC[Keycloak (OIDC)]
  end

  subgraph API[API Layer]
    GW[API Gateway / FastAPI]
    CORE[Core: Tenants • Users • RBAC • Audit]
    CAMO[CAMO Service]
    MRO[MRO Service]
    LOG[Logistics Service]
    REP[Reporting Service]
  end

  subgraph ASYNC[Async / Integration]
    Q[Redis Queue]
    WK[Celery Worker]
    ERP[ERP Systems\nSAP / Symfonia]
    FUTURE[Future: ATL/ELB]
  end

  WEB -->|OIDC| KC
  WEB -->|REST/JSON| GW
  KC -->|JWT / Roles| GW

  GW --> CORE
  GW --> CAMO
  GW --> MRO
  GW --> LOG
  GW --> REP

  CAMO --> Q
  MRO --> Q
  LOG --> Q
  Q --> WK
  WK --> ERP
  WK --> FUTURE
```

---

## 6. Data Architecture

### 6.1 Schema-per-tenant (Mermaid)
```mermaid
flowchart LR
  subgraph PG[(PostgreSQL)]
    SH[shared schema\n(global dictionaries)]
    T1[tenant_airline_a schema]
    T2[tenant_airline_b schema]
    TN[tenant_* schema]
  end

  API --> PG
  SH --- T1
  SH --- T2
  SH --- TN
```

### 6.2 ERD
See `docs/00_product/erd_logical.md`.

---

## 7. Versioning & Release Strategy

- GitHub release procedure: `docs/03_ops/RELEASING_GITHUB.md`
- Semantic Versioning
- v0.x.y for early development
- v1.0.0 for MVP
- Single changelog: `RELEASE_NOTES.md`

---

**End of Document**

## Data import
- PGL Fleet Import: see `docs/01_architecture/database_pgl_import.md` and `db/import/`.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

## ADDENDUM 2026-01-11 — EPIC0B B1 closure (schema-per-tenant E2E)

### Status
CLOSED (PASS w środowisku HTTPS):

* UI `https://app.forgemotionsystems.com` działa i obsługuje OIDC (Authorization Code + PKCE).
* Auth: Keycloak `https://auth.forgemotionsystems.com`.
* API: `https://api.forgemotionsystems.com` z CORS ustawionym na origin UI.
* Tenant routing działa (schema-per-tenant) — request mapowany do schematu po `tenant_id`.

### Runtime kontrakt tenant context

API rozwiązuje `tenant_id` w kolejności (patrz też `docs/02_api/TENANT_CONTEXT.md`):

1. `X-Tenant-Id` — tylko dla `PLATFORM_ADMIN` (override cross-tenant).
2. Claim `tenant_id` w JWT — docelowy tryb produkcyjny.
3. `X-Debug-Tenant-Id` — tylko gdy `DEBUG_TENANT_HEADER=true` (dev/demo).

### Ryzyka / backlog

* UI obecnie może działać na debug header (demo). Produkcyjnie wymagany jest mapper Keycloak dla claim `tenant_id` oraz usunięcie `DEBUG_TENANT_HEADER`.
* Należy utrzymywać osobnego klienta Keycloak dla UI: `aviation-ui` (public + PKCE) i dla API: `aviation-api`.

## ADDENDUM 2026-01-12 — DEV runtime: container ships code via Docker COPY

### Observation
Backend `api` container builds application code into the image (`infra/docker/api.Dockerfile` uses `COPY ... /app`).
Therefore, code changes on the host do not affect the running container unless the image is rebuilt.

### Operational consequence
For DEV backend work (e.g. RBAC changes in Epic #10.1), every code change must be followed by:

```bash
cd infra/docker
docker compose build --no-cache api
docker compose up -d api
docker compose logs -n 80 --no-color api
```

### Recommendation (mini-task)
After closing #10.1, introduce a DEV-only bind-mount (compose override or profile) to mount `apps/api/src` into `/app`.
This must never be enabled in production. See `docs/03_ops/DEV_DOCKER_BIND_MOUNT_MINI_TASK.md`.


## UI #14.3 – Aircraft Context & E2E Prep (Completed)
- Implemented Aircraft Context selector (throttled, cooldown-protected) bound to /v1/aircraft.
- Added ownership badge (OWNER/MRO) and permission flags derived from tenant context.
- Stabilized UI init (dedupe, retry) and cleared ERROR/COOLDOWN after successful fetch.
- Added E2E navigation placeholder; backend E2E flow validated via API (Reservation → ISSUE → RETURN).
- Outcome: UI stable, ready for E2E Step 3 execution.

---
## ADDENDUM 2026-01-15 — DMS (Document Management System) confirmed

### Decision summary
- DMS is a **core subsystem** (not an attachments-only feature).
- Document types are registry-driven; each document has lifecycle, signatures and retention.
- Immutable archive is enforced after `ISSUED`/`SIGNED` depending on type.

### MVP document families
- CAMO: AMP revisions, AD/SB status, ARC, CRS_CAMO
- MRO: Work Orders, Task/Job Cards, CRS_145, RTS package
- STORES: EASA Form 1 (structured + PDF), CoC, tags (serviceable/quarantine)

### Artifacts
- Rendered PDFs and print tags are generated from templates.
- Uploaded scans are allowed only as **attachments bound to a document instance**.



---

## ADDENDUM 2026-01-16 — DMS review pass (docs hardening)

### DMS references
- Architecture: `docs/01_architecture/dms_overview.md`
- ADR: `docs/01_architecture/decisions/ADR-0004-dms-core.md`
- API contract: `docs/02_api/dms.md`

### DEV dependency (Keycloak)
DMS smoke tests are blocked unless DEV Keycloak realm persistence is stable.
See: `docs/03_ops/KEYCLOAK_DEV_REALM_PERSISTENCE.md`.
