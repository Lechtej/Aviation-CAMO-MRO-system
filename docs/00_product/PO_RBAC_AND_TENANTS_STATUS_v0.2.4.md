# Product Status — RBAC & Tenants (v0.2.4)

## Audience
Product Owner / Product Management

## Scope
This document summarizes **product-level implications** of closing AUTH/RBAC
and synchronizing SERVER database state in v0.2.4.
It is **not** a technical specification.

## Current System Status (v0.2.4)

### Authorization & Roles
- Authentication and authorization model is **stable (FROZEN)**.
- User identity and role assignment are handled by **Keycloak**.
- Role capabilities (what a role can do) are defined in **RBAC database tables**.
- No UI for role management is planned at this stage.

### Tenants
- Tenants exist and are readable via API.
- Each tenant is isolated by a dedicated database schema.
- API authorization is enforced per role.

## Sources of Truth (Contract)

| Area | Source of Truth |
|-----|-----------------|
| Users | Keycloak |
| User roles | Keycloak (JWT claims) |
| Role permissions | RBAC Database |
| Tenants | Database + API |
| Tenant data isolation | Database schemas |

## What Product Can Safely Plan Now

### Allowed / Ready
- Per-tenant features (read/write).
- Role-based UI behavior (read-only vs editable).
- Tenant-scoped data imports.
- Business modules assuming tenant isolation.

### Not Allowed Without Architecture Change
- Ad-hoc role creation in UI.
- Runtime modification of RBAC without coordinated DB + Keycloak changes.
- Bypassing tenant isolation.

## Product Risks (Known & Accepted)
- Roles must exist consistently in both Keycloak and RBAC DB.
- Adding/changing roles is a **controlled change**, not a quick config.
- Authorization changes may affect compliance and audit scope.

## What Happens Next (Roadmap Context)
- KROK 4: Tenant bootstrap (operational use).
- KROK 5: Tenant schema provisioning.
- Subsequent steps: business features built on stable RBAC & tenant model.

## Definition of Done (Product View)
- PLATFORM_ADMIN can access tenant list.
- Unauthorized roles are blocked.
- No runtime authorization errors observed.

Generated: 2026-01-10T12:52:29.107065Z


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---

## Update 2026-01-11 – obserwacje RBAC na DEV (na podstawie realnych tokenów)

### Co sprawdziliśmy
- tokeny użytkowników: `camo_lot`, `mro_lotams`, `mro_lst`, `stores_lotams`,
- nagłówki tenant context (`x-tenant-id`, `x-tenant-schema`, `x-tenant-source`),
- dostęp do kluczowych endpointów (z `/openapi.json`).

### Wynik (stan na DEV)
| Endpoint | CAMO (camo_lot) | MRO (mro_*) | STORES (stores_*) | Uwagi |
|---|---:|---:|---:|---|
| `GET /v1/aircraft` | 200 | 403 | 403 | **CAMO-only** – OK |
| `POST /v1/aircraft` | 201/409 | 403 | 403 | **CAMO-only** – OK |
| `GET /v1/maintenance-events?aircraft_id=...` | 200 | 200 | 403 | STORES nie powinien widzieć zdarzeń utrzymaniowych – OK |
| `POST /v1/aircraft/_admin/bootstrap` | 201 | 403 | 403 | **PLATFORM_ADMIN-only** – OK (ochrona danych inicjalnych) |
| `POST /v1/logistics/_admin/bootstrap` | 201 | 403 | 403 | **PLATFORM_ADMIN-only** – OK |
| `GET /v1/tenants` | 200 (po nadaniu `PLATFORM_ADMIN`) | 403 | 403 | Admin-only – OK |
| `GET /v1/logistics/*` | 200 | 200 | 200 | Tymczasowo szerokie – do doprecyzowania w backlogu (patrz niżej) |
| `GET /v1/inventory/parts` | 200 | 200 | 200 | jw. |
| `GET /v1/roles` | 200 | 200 | 200 | jw. |

### Backlog / ToDo (rekomendacja)
1) **Uszczelnić Logistics/Inventory**: docelowo `STORES_*` powinien mieć dostęp do magazynu, ale niekoniecznie MRO/CAMO do wszystkich zasobów (zależnie od procesu e2e).  
2) **Rozdzielić uprawnienia read vs write** w logistyce (np. `STORES_RECEIVING`, `STORES_ISSUING`).  
3) Dodać testy automatyczne „RBAC matrix” (smoke) do pipeline (minimum: 10–15 krytycznych endpointów).  
4) Dla produkcji: rozważyć wyłączenie Direct Access Grants, jeśli UI przechodzi na standard OIDC code flow.

## ADDENDUM (2026-01-11) — EPIC1 DESIGN: Work Orders + Tasks + TaskCards (contract + RBAC)

### Scope
Design-only (no DB migrations in this step). This addendum defines the implementation-ready contract
for EPIC1 (CAMO→MRO Work Orders) to be implemented after B1.

### Domain objects (EPIC1)
- WorkOrder (WO header) → 1..N Tasks → 0..N TaskCards (per Task).
- TaskCards are procedures/instructions (AMM/MPD/CMM/SB/Internal). Import from OEM files is planned (design-only).

### Workflow (statuses)
WorkOrder:
- DRAFT → SENT → ACCEPTED → IN_PROGRESS → READY_FOR_CRS → CLOSED
- READY_FOR_CRS used only if requires_crs=true
- CLOSED requires all tasks DONE

Task:
- OPEN → IN_PROGRESS → DONE
- OPEN|IN_PROGRESS → BLOCKED → IN_PROGRESS|DONE (BLOCKED requires blocked_reason)

### RBAC model (permission-based, DB)
Verified on PROD server DB:
- Existing MRO permissions: mro.work_orders.* and mro.task_cards.*
- No CAMO work order permissions yet (camo.%work_order% empty)

#### EPIC1 permissions to add
CAMO:
- camo.work_orders.view
- camo.work_orders.create
- camo.work_orders.update (DRAFT only)
- camo.work_orders.send
- camo.work_orders.commit_workscope
- camo.work_orders.close (requires_crs=false)

MRO:
- mro.work_orders.accept
- mro.work_orders.ready_for_crs (requires_crs=true)

STORE/INV (design-only):
- inv.work_orders.commit_workscope
- inv.work_orders.reserve
- inv.work_orders.issue
- inv.work_orders.return

B1/CRS (design-only):
- mro.work_orders.crs_sign

#### Recommended role mapping
CAMO:
- CAMO_PLANNER: view, create, update(DRAFT), send
- CAMO_ENGINEER: view (optional update(DRAFT))
- CAMO_MANAGER: view, create, update(DRAFT), send, commit_workscope, close

STORE:
- INVENTORY_CONTROLLER: commit_workscope, reserve, issue, return
- STORES_ISSUING: issue
- STORES_RECEIVING: return

MRO (recommended):
- accept: LINE_MAINT_SUPERVISOR, BASE_MAINT_SUPERVISOR, SHIFT_LEADER, TENANT_ADMIN, PLATFORM_ADMIN
- ready_for_crs: CERTIFYING_STAFF_CAT_B1, RELEASE_TO_SERVICE_AUTHORITY

### Guards (mandatory)
- origin guard: EPIC1 WO are origin="CAMO"; existing internal MRO WO are origin="MRO".
- tenant guard: CAMO tenant vs assigned MRO tenant.
