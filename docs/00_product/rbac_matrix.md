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
