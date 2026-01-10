# RBAC SERVER SYNC — v0.2.4

## Cel
Zsynchronizować **bazę danych na serwerze** do stanu logicznie identycznego jak LOCAL po zamknięciu (FROZEN) AUTH/RBAC.
W tym kroku **nie zmieniamy logiki AUTH/RBAC w kodzie** — tylko stan DB.

## Wykonane na SERWERZE

### 1) Migracja struktury RBAC
Źródło: `db/migrations/public/0003_public_auth_rbac.sql`

Utworzone obiekty (schema: `public`):
- `auth_roles`
- `auth_permissions`
- `auth_role_permissions`
- indeksy wymagane przez model

### 2) Seed katalogu RBAC (v0.2.4)
Źródło: `db/seed/seed_public_auth_rbac_catalog_v0.2.4.sql`

Stan końcowy (SERWER):
- roles = **68**
- permissions = **221**
- mappings = **1116**

### 3) Walidacja API
- `GET /v1/tenants`
  - bez tokenu → **401**
  - z tokenem użytkownika z rolą `PLATFORM_ADMIN` → **200 OK**
- logi API (tail): brak:
  - `UndefinedTable`
  - `ProgrammingError`
  - `relation does not exist`
  - `permission denied`

## Keycloak vs DB — zasada działania
- **Keycloak**: źródło tożsamości, wydaje JWT i role/claims w tokenie.
- **DB (RBAC)**: źródło uprawnień (permissions) i mapowań rola→permission.

Ważne:
- Role w DB **nie synchronizują się automatycznie** do Keycloak.
- Role w Keycloak **nie synchronizują się automatycznie** do DB.
- Aby autoryzacja działała, identyfikatory ról muszą istnieć po obu stronach.

## Definition of Done (KROK 3)
- RBAC tabele istnieją na serwerze.
- Seed RBAC v0.2.4 zaaplikowany.
- `PLATFORM_ADMIN` ma dostęp do `/v1/tenants` (200).
- Brak błędów DB w logach API.

Generated: 2026-01-10T12:31:47.941440Z


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
