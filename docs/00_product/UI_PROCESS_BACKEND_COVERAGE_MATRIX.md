# UI Process ↔ Backend Coverage Matrix (CAMO / MRO / STORES)

## 0. System facts (observed in repo)

### 0.1 Runtime routers (FastAPI)
`apps/api/src/main.py` includes routers:
- **Core / Tenants**: `/v1/tenants`
- **Aircraft**: `/v1/aircraft`
- **Maintenance Events**: `/v1/maintenance-events`
- **Inventory**: `/v1/inventory`
- **Logistics**: `/v1/logistics`
- **DMS**: `/v1/dms`

Not present in runtime code:
- **Work Orders** (`/v1/work-orders`) — only ADR + contract draft.
- **Workforce** (`/v1/workforce/*`) — only ops smoke-test doc, no module.
- **CAMO program modules** (Maintenance Program, AD/SB, Reliability) — no modules.

### 0.2 DB migrations present in repo
- `db/migrations/public/0001_public_core.sql`
- `db/migrations/public/0001_public_tenants_aircraft.sql`
- `db/migrations/public/0002_public_aircraft_registration_history.sql`
- `db/migrations/public/0003_public_auth_rbac.sql`
- `db/migrations/public/0004_public_aircraft_utilization.sql`
- `db/migrations/shared/0001_uom.sql`
- `db/migrations/tenant/0001_inventory.sql`
- `db/migrations/tenant/0002_dms.sql`

**Missing in repo (but referenced/used by code & docs):**
- migrations creating `public.stock_reservations`
- migrations creating `public.stock_transactions`
- migration aligning inventory tables with current ORM (notably `parts.tenant_id`)

---

## 1. Coverage summary (what UI can be “real” today)

| UI Area / Process | Backend readiness | Notes / blockers |
|---|---:|---|
| STORES: Receiving / Inventory / Reservations / Issue / Return | **Partial → usable** | Core endpoints exist in `/v1/logistics` + tenant inventory tables exist. Blockers: missing public ledger migrations in repo + public/tenant table inconsistencies. |
| CAMO: Fleet (Aircraft list/details), MRO access, utilization/counters | **Usable** | Aircraft module is implemented with CAMO guard + mro-access. |
| CAMO: Maintenance Program, AD/SB, Reliability | **Not implemented** | UI can stay mock-only; no API/DB. |
| MRO: Execution / Work Orders lifecycle | **Not implemented** | Work Orders are design-only (ADR-0003 + contract draft). |
| MRO: Workforce Planner | **Not implemented** | Workforce module missing (docs exist only). |
| DMS: Types + Documents + lifecycle actions | **Usable (MVP)** | `/v1/dms/types` + `/v1/dms/documents` + lifecycle endpoints exist; requires tenant migration `0002_dms.sql`. |

---

## 2. Implemented endpoints (runtime)

### 2.1 Core / Tenants (`/v1/tenants`)
Implemented:
- `GET /v1/tenants` (permission: `platform.tenants.view`)
- `POST /v1/tenants` (permission: `platform.tenants.create`)

DB dependencies:
- public tenants catalog (from `0001_public_tenants_aircraft.sql`)
- public RBAC catalog (from `0003_public_auth_rbac.sql`)

Gaps:
- UI/Docs sometimes reference `/v1/roles` — **no router present** (docs drift risk).

### 2.2 Aircraft (`/v1/aircraft`)
Implemented (selected):
- CRUD: `GET /v1/aircraft`, `POST`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`
- MRO access: `GET/POST/DELETE /{aircraft_id}/mro-access`
- Utilization: `POST /{aircraft_id}/utilization`, `GET /{aircraft_id}/utilization`
- Counters: `GET /{aircraft_id}/counters`
- Aircraft-scoped maintenance events: `GET/POST/PUT /{aircraft_id}/maintenance-events` (in aircraft router)

DB dependencies:
- public aircraft tables (+ registration history + utilization) from public migrations.

Gaps vs UI “process cockpit” needs:
- No Work Orders linkage (aircraft → WO list) because WO module missing.

### 2.3 Maintenance Events (`/v1/maintenance-events`)
Implemented:
- `GET /v1/maintenance-events`
- `POST /v1/maintenance-events`
- `PATCH /v1/maintenance-events/{event_id}`

DB dependencies:
- event tables (defined in public migrations; verify consistency with current models in runtime).

### 2.4 Inventory (`/v1/inventory`)
Implemented:
- `GET /v1/inventory/parts`
- `POST /v1/inventory/parts`
- `GET/PUT/DELETE /v1/inventory/parts/{part_id}`

DB dependencies:
- tenant tables `parts` from `tenant/0001_inventory.sql`

Critical gap:
- Inventory router enforces `parts.tenant_id`, and logistics ORM defines `Part.tenant_id` as a column,
  but `tenant/0001_inventory.sql` does **NOT** create `tenant_id`.
  → requires migration: `ALTER TABLE parts ADD COLUMN tenant_id uuid;` + backfill + index.

### 2.5 Logistics (`/v1/logistics`)
Implemented (selected):
- UoM: `GET /v1/logistics/uom` (uses `shared.uom` from shared migration)
- Parts/Warehouses/Locations/Stock Items: CRUD endpoints
- Reservations: `GET/POST /v1/logistics/stock-reservations`
- Transactions: `POST /v1/logistics/stock-transactions` (RECEIPT/ISSUE/RETURN, idempotency)

DB dependencies (as implemented in code):
- tenant tables (via SQLAlchemy models without explicit schema):
  - `parts`, `warehouses`, `locations`, `stock_items` (tenant schema via `search_path`)
- public tables (hardcoded in SQL text):
  - `public.stock_reservations`
  - `public.stock_transactions`

Critical inconsistencies / risks:
1) **Repo does not contain migrations** for `public.stock_reservations` and `public.stock_transactions`,
   but code writes/reads them.
   → environments are not reproducible.
2) Idempotency replay path reads `qty_on_hand` from `public.stock_items` (hardcoded SQL),
   while stock items are tenant tables (`stock_items` in tenant schema).
   → potential runtime bug / wrong schema read.
3) Documentation `docs/02_api/logistics.md` claims some inventory tables are in `public`,
   while migrations create them as **tenant** tables.
   → doc drift.

### 2.6 DMS (`/v1/dms`)
Implemented:
- Types: `GET/POST /v1/dms/types`
- Documents: `GET/POST /v1/dms/documents`, `GET /documents/{id}`
- Lifecycle actions: `/review`, `/approve`, `/issue`, `/sign`, `/archive`

DB dependencies:
- tenant migration `tenant/0002_dms.sql` (document tables)
- seeded document types (scripts/seed or bootstrap path)

Known recently fixed behavior:
- domain literal validation for EASA type alignment (UI thread #21.2).

---

## 3. UI process readiness mapping (mockups → API/DB)

### P1. CAMO → MRO → STORES (end-to-end)
Target UI steps:
1) CAMO Planner Cockpit
2) CAMO Maintenance Demand (MP/AD/SB/Reliability)
3) Work Order (handoff CAMO → MRO)
4) MRO Execution (WO lifecycle)
5) STORES Reservation
6) STORES Issue / Return
7) Status back to CAMO

Backend coverage:
- Step 1: **Partial** (Aircraft list/utilization exists; cockpit KPIs likely mock-only).
- Step 2: **Missing** (no MP/AD/SB/Reliability models).
- Step 3–4: **Missing** (Work Orders not implemented).
- Step 5–6: **Usable** (Reservations + Transactions exist; needs DB/migrations normalized).
- Step 7: **Missing** (WO status + CAMO/MRO handshake absent).

Minimal backend needed to make P1 “real”:
- Implement `Work Orders` (ADR-0003) with status machine + minimal fields:
  - `id`, `aircraft_id`, `origin` (CAMO), `assigned_mro_tenant_id`, `status`,
    `created_at/by`, `updated_at/by`
- Define stable linkage for stores:
  - `stock_reservations.source_ref_type = "WORK_ORDER"`
  - `stock_reservations.source_ref_id = work_order_id`

DB additions (high level):
- tenant tables: `work_orders`, `work_order_tasks` (or equivalent)
- indexes for lookup by `aircraft_id`, `status`, `assigned_mro_tenant_id`

### P2. MRO Execution (WO lifecycle + Workforce)
Backend coverage:
- Work Orders: **Missing**
- Workforce: **Missing**
- Stores integration: **Partial** (stock flow exists but lacks WO anchors)

DB additions:
- `employees`, `qualifications`, `assignments` (minimum for planner UI)
- link tables: `work_order_task_assignments`

### P3. STORES WMS-ready (desktop + tablet readiness)
Backend coverage:
- Inventory + reservations + transactions: **Partial**
- Missing WMS primitives (for future): moves, putaway, cycle count, scanning events.

DB additions (future, not required for mock UI):
- `stock_moves` (or event ledger), `receipts`, `putaway_tasks`, `inventory_counts`

---

## 4. DB / Migration gap list (must-fix to avoid UI/backend drift)

### 4.1 Public ledger tables used by code but absent in repo
Required migrations to add:
- `public.stock_reservations`
- `public.stock_transactions`
- constraints + indexes:
  - `UNIQUE(tenant_id, idempotency_key)` on transactions
  - `INDEX(tenant_id, created_at)` for lists
  - FK strategy: either soft refs or explicit FK to tenant stock tables (careful with schema-per-tenant)

### 4.2 Tenant inventory tables out of sync with ORM/runtime
Observed mismatch:
- ORM uses `parts.tenant_id` (Inventory endpoints filter on it)
- tenant migration `0001_inventory.sql` does not create it

Required migration:
- `ALTER TABLE parts ADD COLUMN tenant_id uuid;`
- backfill strategy:
  - for existing rows: set tenant_id to current tenant during migration run (or allow null and enforce at API level temporarily)
- add index:
  - `CREATE INDEX ON parts(tenant_id, part_number);` (and/or unique constraint scoping)

### 4.3 Schema usage inconsistencies (public vs tenant)
Current state:
- `parts/warehouses/locations/stock_items` are tenant tables (migration `tenant/0001_inventory.sql`)
- reservations/transactions are forced into `public.*` via SQL text

Decision required (choose one and align code + docs):
- **Option A (recommended):** Tenant tables for stock state, public for cross-tenant catalogs and append-only ledgers with tenant_id.
- **Option B:** Public tables for everything with tenant_id filters (simplifies SQL, reduces search_path dependence).

### 4.4 Known potential bug in idempotency replay path
`/v1/logistics/stock-transactions` replay reads:
- `SELECT qty_on_hand FROM public.stock_items ...`
but stock state is in tenant `stock_items`.
Action:
- replace with tenant-scoped table access (no `public.` prefix) or ensure stock_items is actually public (but then migration must reflect it).

---

## 5. What is sufficient already for UI mockups (recommendation)
For clickable mockups that also optionally call API (in future), the current backend is sufficient to support:
- Fleet selection and aircraft context (CAMO cockpit subset)
- Stores: create/list reservations, create transactions (receipt/issue/return)
- DMS: list/create document types and documents + basic lifecycle actions

Everything else required for full CAMO↔MRO process execution must be implemented:
- Work Orders + Tasks (+ minimal status engine)
- Workforce + assignments
- CAMO program demand generators (MP/AD/SB/Reliability)

---

## Appendix - UI Auth + Tenant Context (Incognito / first run)

UI wymagane jest ustawienie `X-Tenant-Id` dla większości endpointow domenowych.
Dla sytuacji, gdy token nie niesie claimu `tenant_id` (szczegolnie Incognito / fresh profile), UI wykonuje bootstrap przez `GET /v1/tenants` (Authorization-only) i zapisuje do localStorage: `tenant_id`, `tenant_uuid` (legacy), `tenant_schema`.
Szczegoly: `docs/02_api/TENANT_CONTEXT.md` (Addendum 2026-01-17).

---

### 2026-01-18 — UI aircraft context stabilization (implementation note)

- `apps/web/app.js` contains an embedded **Aircraft Context** block (UI-only) which:
  - enforces **AUTH GATE** (no `/v1/aircraft` call before login),
  - ensures tenant context exists (uses `tenant_uuid` from storage; optional one-time `/v1/tenants` discovery for Incognito),
  - throttles/retries to avoid request storms.

Current status:
- Navigation/buttons: **PASS**
- Aircraft list rendering on `/camo/aircraft`: **FAIL** (tracked in #14.8)
