# EPIC1 — Work Orders Contract (design-only)

Date: 2026-01-11
Scope: design-only (implementation after B1)
Applies to: CAMO→MRO Work Orders (origin="CAMO")

## Entities
### WorkOrder
Fields (minimum):
- id (uuid)
- origin = "CAMO" | "MRO"
- tenant_id (uuid) — CAMO owner tenant
- assigned_mro_tenant_id (uuid) — execution tenant
- aircraft_id (uuid)
- due_date (date/datetime)
- requires_crs (bool)
- status (enum)
- audit: created_by_user_id, sent_at, accepted_at, closed_at
- version (int)

### Task
- id, work_order_id
- code, title, description
- required_qualifications (string[])
- status, blocked_reason
- version

### TaskCard (0..N per Task)
- id, task_id
- source_type (AMM|MPD|CMM|SB|INTERNAL)
- source_ref, revision
- title
- content_format (JSON|HTML|PDF_REF)
- content
- version
Import from OEM files planned (separate epic).

## Statuses
WorkOrder:
DRAFT → SENT → ACCEPTED → IN_PROGRESS → (READY_FOR_CRS) → CLOSED

Rules:
- READY_FOR_CRS only if requires_crs=true
- CLOSED requires all tasks DONE
- assigned_mro_tenant_id immutable after SENT

Task:
OPEN → IN_PROGRESS → DONE
OPEN|IN_PROGRESS → BLOCKED → IN_PROGRESS|DONE (BLOCKED requires blocked_reason)

## RBAC and guards
Mandatory guards:
- origin guard: EPIC1 endpoints operate on origin="CAMO" only
- tenant guard:
  - CAMO: caller.tenant_id == work_order.tenant_id
  - MRO: caller.tenant_id == work_order.assigned_mro_tenant_id

Permission model: DB permissions (role→permission mapping).
EPIC1 adds CAMO permissions and a small MRO delta.

## Permissions (EPIC1 delta)
CAMO (new): camo.work_orders.view/create/update/send/commit_workscope/close
MRO (new): mro.work_orders.accept, mro.work_orders.ready_for_crs
INV (design-only): inv.work_orders.commit_workscope/reserve/issue/return
CRS (design-only): mro.work_orders.crs_sign

## Minimal REST endpoints
Base: /v1/work-orders

CAMO:
- POST   /v1/work-orders
- PATCH  /v1/work-orders/{id}           (DRAFT only)
- POST   /v1/work-orders/{id}/send
- POST   /v1/work-orders/{id}/commit-workscope  (CAMO or INV)
- POST   /v1/work-orders/{id}/close     (requires_crs=false)

MRO:
- POST   /v1/work-orders/{id}/accept
- POST   /v1/work-orders/{id}/start
- POST   /v1/work-orders/{id}/pause     (optional, existing permission)
- POST   /v1/work-orders/{id}/complete  (optional, existing permission)
- POST   /v1/work-orders/{id}/ready-for-crs   (requires_crs=true)
- POST   /v1/work-orders/{id}/tasks/{task_id}/status

TaskCards (existing perms):
- GET/POST /v1/work-orders/{id}/tasks/{task_id}/task-cards
- GET      /v1/task-cards/{task_card_id}
