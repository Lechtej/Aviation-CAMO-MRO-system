# WBS — Aviation CAMO & MRO Platform

## Core Platform
- Tenant Management
- User & Role Management (RBAC)
- Audit Trail & Event Log
- Configuration & Dictionaries
- Reporting & Export Engine

## CAMO Module
- Aircraft & Fleet
- Configuration & ATA (baseline)
- Maintenance Program (AMP)
- Due List & Forecast
- Defects & Deferred (bridge to ATL)

## MRO Module
- Work Orders
- Task Cards
- Workflow & Status Engine
- Sign-off & Authorizations

## Logistics Module (Shared)
- Part Master Data
- Inventory & Warehouses
- Rotables & Pool
- Consumables & Expendables
- Inventory Movements
- Cost Allocation

## Integration Layer
- API Gateway
- ERP Connectors
- Message Queue & Retry
- Integration Monitoring


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
