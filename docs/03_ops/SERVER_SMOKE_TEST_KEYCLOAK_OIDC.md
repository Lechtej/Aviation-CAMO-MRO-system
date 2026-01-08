# Server Smoke Test – Keycloak / OIDC (client_credentials)

## Scope
Server-side smoke test for AviationCAMO-MRO-system:
- Keycloak OIDC
- client_credentials
- PLATFORM_ADMIN
- Tenant bootstrap
- Logistics & Inventory happy-path

---

## Preconditions
- Docker + docker-compose
- keycloak / api / postgres containers running

---

## Token
Use client_credentials.
Regenerate often (short TTL).

---

## Tenant
Create tenant via /v1/tenants.
All tenant endpoints require X-Tenant-Id header.

---

## Logistics bootstrap
POST /v1/logistics/_admin/bootstrap

---

## Happy-path
- inventory part
- warehouse
- location
- stock-item

---

## Known issue
POST /v1/logistics/movements → 404 Not Found
