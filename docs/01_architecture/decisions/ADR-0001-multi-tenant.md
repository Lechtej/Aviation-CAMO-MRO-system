# ADR-0001 — Multi-tenant SaaS

- Status: Approved
- Date: 2026-01-05
- Decision: Multi-tenant architecture for multiple airlines in one platform.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
