# Architecture Overview (High-Level)


## 🔐 Authentication & Authorization – STATUS FREEZE (2026-01-09)

### Scope
This section documents **closure and confirmation** of:
- Authentication (Keycloak)
- Authorization (RBAC DB)
- Keycloak ↔ API ↔ Database integration

### Final Architecture (confirmed)
- **IdP**: Keycloak 25.0
- **Realm**: `aviation`
- **Client**: `aviation-api`
- **Grant type (local dev)**: `password`
- **Token**: JWT (Bearer)
- **RBAC source of truth**: PostgreSQL (`public.auth_*`)
- **Enforcement**: FastAPI middleware + RBAC DB lookup

### Data Flow (confirmed)
1. User authenticates in Keycloak
2. JWT contains `realm_access.roles`
3. API extracts roles from token
4. API resolves permissions via DB tables:
   - `public.auth_roles`
   - `public.auth_permissions`
   - `public.auth_role_permissions`
5. Endpoint-level permission check enforced (`require_permission(...)`)

### Verification Status
| Element | Status |
|---|---|
| Keycloak realm reachable | ✅ |
| Token issuance (password grant) | ✅ |
| JWT role propagation | ✅ |
| RBAC tables present | ✅ |
| RBAC seed applied | ✅ |
| API permission enforcement | ✅ |
| Unauthorized access blocked | ✅ |

**Status: CLOSED / FROZEN**  
No further changes in this layer without a version bump + new migration/seed.

## Runtime Components
- Web UI (React/TypeScript)
- API (FastAPI)
- Worker (Celery)
- PostgreSQL (schema-per-tenant)
- Redis (queue)
- Keycloak (OIDC)

## Principles
- Tenant isolation via PostgreSQL schemas
- Auditability by design (immutable audit events)
- Integration layer with retry + idempotency


## Modules (WBS)
See: `docs/01_architecture/wbs_modules.md`.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

## EPIC1 — Work Orders (design-only) [2026-01-11]

### Concept
EPIC1 introduces CAMO-originated Work Orders executed by an assigned MRO tenant:
WorkOrder (header) → 1..N Tasks → 0..N TaskCards.

### Key design flags
- origin: CAMO | MRO (EPIC1 uses origin="CAMO")
- requires_crs: boolean (enables READY_FOR_CRS and CRS signing flow)

### RBAC
Permission-based (DB). EPIC1 adds camo.work_orders.* and a small delta to existing MRO permissions.
See: docs/02_api/work_orders_contract.md
