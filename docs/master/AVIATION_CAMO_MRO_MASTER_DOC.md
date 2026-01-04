# AVIATION CAMO & MRO PLATFORM — MASTER DOCUMENT

**Version:** v0.1.1 (Documentation Update)  
**Status:** Approved baseline  
**Date:** 2026-01-05

**Runtime Baseline:** v0.2.1 (Docker Compose verified target)  

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
- Semantic Versioning
- v0.x.y for early development
- v1.0.0 for MVP
- Single changelog: `RELEASE_NOTES.md`

---

**End of Document**
