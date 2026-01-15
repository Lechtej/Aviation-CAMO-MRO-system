# WBS — Modules & Milestones (High-Level)

> Goal: deliver CAMO + MRO + Inventory/Logistics + ATL on a shared Platform layer, with multi-tenant isolation via PostgreSQL schema-per-tenant.

## 1. Platform (Cross-cutting)
1.1 Identity & Access (Keycloak/OIDC, JWT verification, RBAC, scopes)  
1.2 Tenant management (schema-per-tenant lifecycle, tenant bootstrap, admin endpoints)  
1.3 Audit trail (immutable events, who/what/when, correlation IDs)  
1.4 Observability (structured logs, metrics, tracing; health/readiness)  
1.5 Background jobs (Celery tasks, retries, idempotency)  
1.6 API governance (OpenAPI contract-first, versioning, error model)

## 2. Inventory / Logistics
2.1 Dictionaries: Part master, UoM (shared), Warehouses, Locations/Bins  
2.2 Stock states: on-hand / reserved / in-transit (initial model)  
2.3 Rotables vs consumables/expedables (type + rules)  
2.4 Pool marker and ownership model (tenant-owned vs pooled)  
2.5 Movements (receive/issue/transfer) — later (needs audit + idempotency)  
2.6 Reservations & allocations — later  
2.7 Valuation & cost entries — later

## 3. CAMO
3.1 Aircraft type / aircraft master  
3.2 Maintenance program (MPD/AMP) placeholders  
3.3 AD/SB tracking placeholders  
3.4 Planning / due lists placeholders  
3.5 Interfaces to MRO (work package creation) — later

## 4. MRO
4.1 Work orders / work packages placeholders  
4.2 Tasks / findings placeholders  
4.3 Tooling/calibration placeholders  
4.4 Material consumption interface to Inventory — later  
4.5 Release to service / documentation — later

## 5. ATL (Aircraft Technical Log)
5.1 Flight / sector record placeholders  
5.2 Defects & rectifications placeholders  
5.3 Deferred defects (MEL/CDL) placeholders  
5.4 Attachments and signatures — later

## 6. Integrations
6.1 ERP/Accounting adapters (SAP, Symfonia) — async export + reconciliation  
6.2 Part master sync — later  
6.3 EDI / messaging layer — later

## Near-term milestones (suggested)
- M1: Platform foundation (tenant + auth + minimal RBAC) ✅ done (v0.2.6 line)
- M2: Inventory skeleton (Part + Warehouse + Location + Stock state) ✅ this ZIP (v0.2.7)
- M3: Movements + reservations (Inventory) + audit events
- M4: CAMO/MRO placeholders expanded + cross-module contract
- M5: ATL skeleton + integrations scaffolding


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-15 — DMS baseline

- DMS introduced as core subsystem (Document ≠ attachment).
- Registry-driven document types, lifecycle, signatures and archive are planned as Platform 1.7.

