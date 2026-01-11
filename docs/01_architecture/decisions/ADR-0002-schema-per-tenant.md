# ADR-0002 — PostgreSQL schema-per-tenant

- Status: Approved
- Date: 2026-01-05
- Decision: Use PostgreSQL schema-per-tenant for tenant isolation.
- Rationale: Strong isolation and audit clarity.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## Addendum 2026-01-11 — Runtime routing contract (B1)

### Routing inputs
- **Access token claim**: `tenant_id` (UUID) — target input for production.
- **Admin override header**: `X-Tenant-Id` — allowed only for `PLATFORM_ADMIN`.
- **Debug override header**: `X-Debug-Tenant-Id` — allowed only when `DEBUG_TENANT_HEADER=true`.

### Routing outputs (observability)
API includes response headers for traceability:
- `x-tenant-id`
- `x-tenant-schema`
- `x-tenant-source` (e.g. `token(tenant_id)`, `header(admin)`, `header(debug)`)

### Security constraints
- Debug header must never be enabled by default in PROD.
- Admin override must be role-gated (`PLATFORM_ADMIN`).
- Token-based routing remains the long-term contract; debug header is a bootstrap mechanism for early E2E.

## ADDENDUM 2026-01-11 — Tenant context resolution (runtime contract)

### Decision clarification: request → tenant schema mapping
**Routing key:** `tenant_id` (UUID) resolved per request and mapped via `public.tenants.schema_name`.

**Resolution order (implemented in API middleware):**
1. `X-Tenant-Id` header when requester has `PLATFORM_ADMIN` (admin override).
2. `tenant_id` claim from access token (primary intended PROD path).
3. `X-Debug-Tenant-Id` header only when `DEBUG_TENANT_HEADER=true` (explicit, non-prod).

**Diagnostics contract:** API MAY return these headers to aid operations:
- `X-Tenant-Id`: resolved tenant UUID
- `X-Tenant-Schema`: resolved schema name (e.g. `t_aca`)
- `X-Tenant-Source`: `header(admin)` / `token(claim)` / `header(debug)`

### Risk controls
- Debug header must be disabled by default and treated as a temporary E2E bootstrap.
- Admin header must be enforced by role (`PLATFORM_ADMIN`) and logged.

## ADDENDUM 2026-01-11 — runtime tenant routing algorithm (B1)

### Runtime algorithm (kolejność źródeł)

1) `X-Tenant-Id` — tylko gdy użytkownik ma rolę `PLATFORM_ADMIN` (narzędzie administracyjne / operacyjne).
2) Token claim `tenant_id` — docelowy mechanizm produkcyjny.
3) `X-Debug-Tenant-Id` — tylko gdy `DEBUG_TENANT_HEADER=true` (dev/demo).

Jeżeli tenant nie został rozpoznany → request kończy się błędem 400/401 (wg implementacji), brak dostępu do DB.

### Observability (debug headers)

API może zwracać:
- `x-tenant-id`
- `x-tenant-schema`
- `x-tenant-source`

To jest świadome ułatwienie testów E2E (do wyłączenia lub ograniczenia w audycie, jeśli wymagane).

### Security notes

- `X-Debug-Tenant-Id` jest świadomie **niebezpieczne** w prod (tenant spoofing) → wyłączone domyślnie.
- `X-Tenant-Id` ograniczone do `PLATFORM_ADMIN` i powinno być logowane/audytowane.
- `tenant_id` w tokenie to jedyny mechanizm, który skaluje audytowo.

## ADDENDUM 2026-01-11 - Routing implementation notes

### Implementacja (MVP)

* API uzywa *schema-per-tenant* w Postgres: `t_<tenant_code>`.
* Tenant context jest ustalany w middleware warstwa HTTP, a nastepnie:
  * wpinany w `request.state.tenant_id` oraz `request.state.tenant_schema`,
  * wykorzystywany do ustawienia `search_path` na polaczeniu DB (SQLAlchemy).

### Resolution order (kontrakt)

1. `X-Tenant-Id` (tylko `PLATFORM_ADMIN`) - operacje cross-tenant.
2. JWT claim `tenant_id` - tryb docelowy.
3. `X-Debug-Tenant-Id` (tylko gdy `DEBUG_TENANT_HEADER=true`) - tryb E2E/dev.

### Guardrails

* W prod: `DEBUG_TENANT_HEADER=false`.
* Wszystkie endpointy tenantowe loguja `tenant_id` i `tenant_schema` w response headers (debug).

## ADDENDUM 2026-01-11 - Tenant context resolution order (implemented)

Implementacja w API (middleware) rozwiązuje tenant w następującej kolejności:

1. **Header `X-Tenant-Id`** - tylko dla roli `PLATFORM_ADMIN` (operacje cross-tenant)
2. **Claim `tenant_id` w JWT** - docelowa ścieżka produkcyjna (Keycloak mapper)
3. **Header `X-Debug-Tenant-Id`** - tylko gdy `DEBUG_TENANT_HEADER=true` (dev/demo)

DoDo / ryzyka:
* `X-Debug-Tenant-Id` musi być domyślnie wyłączony w PROD (inaczej obejście izolacji tenantów).
* Mapper `tenant_id` w Keycloak jest wymagany, aby UI/API mogły działać bez debug headerów.
