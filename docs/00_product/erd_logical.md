# ERD (Logical) — MVP Baseline

> This is a *logical* ERD for MVP baseline (CAMO + MRO + Logistics).
> Physical schema design will follow schema-per-tenant.

```mermaid
erDiagram
  TENANT ||--o{ USER : has
  USER ||--o{ USER_ROLE : assigned
  ROLE ||--o{ USER_ROLE : contains
  TENANT ||--o{ AIRCRAFT : owns
  AIRCRAFT ||--o{ WORK_ORDER : has
  WORK_ORDER ||--o{ WORK_ORDER_TASK : contains
  WORK_ORDER_TASK ||--o{ SIGN_OFF : signed
  MAINTENANCE_PROGRAM ||--o{ MAINTENANCE_TASK : includes
  AIRCRAFT ||--o{ TASK_EXECUTION : tracks
  MAINTENANCE_TASK ||--o{ TASK_EXECUTION : executed
  PART ||--o{ INVENTORY_ITEM : defines
  INVENTORY_ITEM ||--o{ INVENTORY_MOVEMENT : moves
  WORK_ORDER ||--o{ COST_ENTRY : costs
```

## Entity Notes
- All domain entities include `tenant_id` and audit fields.
- No hard deletes; use status-based lifecycle.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
