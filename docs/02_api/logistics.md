## Update: RBAC for POST /v1/logistics/stock-transactions (Epic #10.1)

**Scope**
Adds role-based access control to stock transactions by transaction type, enforced server-side before business logic.

**Endpoint**
- `POST /v1/logistics/stock-transactions`

**Transaction types**
- `RECEIPT`
- `ISSUE`
- `RETURN`

**Effective roles (Keycloak → API)**
- Store / Logistics: `LOGISTICS_OFFICER`
- Mechanic: `MECHANIC`
- CAMO Planner: `CAMO_PLANNER`
- Admins: `PLATFORM_ADMIN`, `TENANT_ADMIN`

**Authorization matrix**
- `RECEIPT`: `LOGISTICS_OFFICER` (admins allowed)
- `ISSUE`: `LOGISTICS_OFFICER` or `MECHANIC`
  - `CAMO_PLANNER`: **only with reservation** (future field; currently denied)
- `RETURN`: `LOGISTICS_OFFICER` or `MECHANIC`
- Admins: full access

**Enforcement**
- Guard executes **before** stock mutation.
- Missing role → `403`.
- Invalid type → `422`.

**DEV/runtime note**
API container runs code from image path `/app`. Any host-side code changes require
`docker compose build --no-cache api` (no bind-mount in DEV).

**Verification (curl)**
Validated with black-and-white tests:
- MECH + RECEIPT → 403
- MECH + ISSUE → 201
- STORE + RECEIPT → 201
- CAMO + ISSUE (no reservation) → 403
