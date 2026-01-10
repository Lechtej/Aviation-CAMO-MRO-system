# ADR-006: Brak bezpośredniego RBAC bridge z Keycloak

Status: Accepted
Data: 2026-01-10

## Kontekst
RBAC utrzymywany jest w bazie aplikacji. Keycloak pełni rolę IdP.

## Decyzja
Nie implementujemy bridge RBAC z Keycloak.

## Konsekwencje
- DB jako źródło prawdy
- KC tylko JWT


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
