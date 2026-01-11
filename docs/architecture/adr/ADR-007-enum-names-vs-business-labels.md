# ADR-007: Enum names vs Business labels

Date: 2026-01-11
Status: Accepted

## Context
The system uses enums in APIs and databases (e.g. stock conditions, reorder modes).
Business stakeholders may want to rename or rephrase these concepts in UI or documentation.

## Decision
We distinguish between:
- **Technical enum identifiers** – stable, contractual, machine-facing.
- **Business labels** – human-facing, changeable, localized.

Business labels may evolve without changing enum identifiers.

## Consequences
- API and DB remain stable over time.
- UI can adapt wording without migrations.
- Any enum rename requires explicit ADR + migration.

## Examples
- `ALERT_ONLY` → UI label: “Low stock alert”
- `DRAFT_REQUISITION` → UI label: “Automatic replenishment request”
