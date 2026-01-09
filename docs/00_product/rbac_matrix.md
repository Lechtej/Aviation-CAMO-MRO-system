# RBAC Matrix — MVP Baseline

## Permission Groups
- CORE: manage_tenants, manage_users, manage_roles, view_audit, view_reports
- CAMO: view_aircraft, edit_aircraft, manage_program, manage_due, manage_defects
- MRO: manage_workorders, manage_tasks, sign_off
- LOGISTICS: manage_parts, manage_inventory, manage_movements, manage_costs
- INTEGRATION: view_integrations, retry_integrations

## Role → Permissions (MVP)
- Platform Admin: CORE(all) + INTEGRATION(all)
- Tenant Admin: CORE(manage_users, manage_roles, view_audit, view_reports) + INTEGRATION(view_integrations)
- Auditor: CORE(view_audit, view_reports) + CAMO(view*) + MRO(view*) + LOGISTICS(view*)
- CAMO Planner: CAMO(view_aircraft, manage_program, manage_due, manage_defects)
- CAMO Engineer: CAMO(view_aircraft, edit_aircraft, manage_defects) + LOGISTICS(view_inventory)
- Maintenance Planner: MRO(manage_workorders, manage_tasks) + LOGISTICS(view_inventory)
- Mechanic: MRO(manage_tasks) + LOGISTICS(manage_movements)
- Certifying Staff: MRO(sign_off) + MRO(view*)
- Logistics Officer: LOGISTICS(all) + CORE(view_reports)
- Finance / Cost Controller: LOGISTICS(manage_costs, view_inventory) + CORE(view_reports)

## Notes
- RBAC is action-based (permissions), not screen-based.
- All sign-off actions must be auditable.

## v0.2.4 — DB-backed RBAC Catalog (authoritative)

**Source of truth: Postgres (public schema)**  
Roles and permissions are seeded to DB and can be used by the API for authorization checks.

### Catalog tables
- `public.auth_roles` — role catalog (code, scope, description)
- `public.auth_permissions` — permission catalog (code, domain, description)
- `public.auth_role_permissions` — many-to-many mapping

### Permission naming convention
- Format: `<domain>.<area>.<action>` (lowercase, dot-separated)
- Examples:
  - `tenant.users.assign_roles`
  - `camo.work_packages.release`
  - `mro.certification.sign_crs`
  - `inv.stock.adjust`

### Keycloak alignment (contract)
Keycloak role codes **must match** `public.auth_roles.code` (exact string match).  
JWT → API should carry `realm_access.roles[]` and the API maps them to `auth_roles` → permissions.

### Notes
- Contextual access (e.g. per-aircraft/MRO relationship) remains separate from this global catalog.
- Sign-off actions (CRS/RTS) require dedicated permissions and must be auditable (event log).
