# ADR-0003: EPIC1 Work Orders (CAMO→MRO) — Model + RBAC (permission-based) + CRS option

Date: 2026-01-11
Status: Accepted
Scope: Design-only (no DB migrations in this ADR)

## Context
We need an auditable model for CAMO-originated maintenance requests executed by an MRO tenant.
Some Work Orders require CRS / release-to-service action, but many do not (e.g., minor servicing).
The design must support future OEM procedure import (AMM/MPD/CMM/SB) and align with permission-based RBAC.

Compliance-friendly note:
This ADR models workflow and authorizations suitable for controlled maintenance environments.
It does not claim regulatory completeness; final sign-off and compliance responsibilities remain organizational/regulatory.

## Decision
1) Model:
WorkOrder (header) → 1..N Tasks → 0..N TaskCards.

2) CRS as option:
- requires_crs=true enables READY_FOR_CRS and CRS signing action (design-only).
- requires_crs=false allows closing without CRS.

3) Separate origins:
- origin="CAMO" for CAMO→MRO orders (EPIC1)
- origin="MRO" for internal MRO work orders
Prevents collision with existing permissions such as mro.work_orders.create.

4) RBAC:
- enforce permissions from DB (role→permission mapping)
- add camo.work_orders.* and minimal MRO delta (accept, ready_for_crs)
- keep tenant boundary as hard guard (CAMO tenant vs assigned MRO tenant)

5) commit-workscope:
Idempotent action called by CAMO or INV to freeze scope and enable inventory flows (design-only).

## Status model
WorkOrder:
DRAFT → SENT → ACCEPTED → IN_PROGRESS → (READY_FOR_CRS) → CLOSED
Task:
OPEN → IN_PROGRESS → DONE (+ optional BLOCKED with reason)

## Consequences
- Compatible with existing RBAC model and existing MRO permissions.
- Enables controlled separation CAMO orders vs MRO-internal orders.
- Provides base for OEM TaskCard import and structured sign-off flows.
- Implementation deferred until after B1 (first migration introducing WorkOrder tables).
