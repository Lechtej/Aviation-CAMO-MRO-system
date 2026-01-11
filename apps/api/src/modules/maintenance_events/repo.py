from __future__ import annotations

from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class MaintenanceEventsRepo:
    """Single DB access layer for EPIC2.

    Important:
    - all DB access for maintenance events MUST go through this repo
      so we can later plug schema-routing (B1) without touching endpoints.
    """

    def __init__(self, db: Session):
        self.db = db

    def aircraft_owner_tenant_id(self, aircraft_id: UUID) -> Optional[UUID]:
        row = self.db.execute(
            text("SELECT owner_tenant_id FROM public.aircraft WHERE id = :id"),
            {"id": str(aircraft_id)},
        ).fetchone()
        if not row:
            return None
        return UUID(str(row.owner_tenant_id))

    def mro_has_access(self, mro_tenant_id: UUID, aircraft_id: UUID) -> bool:
        row = self.db.execute(
            text(
                """
                SELECT 1
                FROM public.aircraft_mro_access ama
                WHERE ama.aircraft_id = :aircraft_id
                  AND ama.mro_tenant_id = :mro_tenant_id
                  AND ama.active IS TRUE
                LIMIT 1
                """
            ),
            {"aircraft_id": str(aircraft_id), "mro_tenant_id": str(mro_tenant_id)},
        ).fetchone()
        return bool(row)

    def list_visible_events(
        self,
        *,
        tenant_id: UUID,
        allow_owner: bool,
        allow_mro_assigned: bool,
        aircraft_id: Optional[UUID] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return events visible to tenant.

        Rules:
        - owner: events where aircraft.owner_tenant_id == tenant_id
        - mro: events where exists aircraft_mro_access(active) for tenant_id
        """

        params: dict[str, Any] = {"tenant_id": str(tenant_id), "limit": int(limit)}

        # visibility part vs optional aircraft filter
        vis_parts: list[str] = []
        if allow_owner:
            vis_parts.append("a.owner_tenant_id = :tenant_id")
        if allow_mro_assigned:
            vis_parts.append(
                """
                EXISTS (
                    SELECT 1
                    FROM public.aircraft_mro_access ama
                    WHERE ama.aircraft_id = e.aircraft_id
                      AND ama.mro_tenant_id = :tenant_id
                      AND ama.active IS TRUE
                )
                """
            )
        if not vis_parts:
            return []
        vis_sql = "(" + " OR ".join(vis_parts) + ")"
        extra_sql = ""
        if aircraft_id:
            params["aircraft_id"] = str(aircraft_id)
            extra_sql = " AND e.aircraft_id = :aircraft_id"

        rows = self.db.execute(
            text(
                f"""
                SELECT
                    e.id,
                    e.aircraft_id,
                    e.created_by_tenant_id,
                    e.event_type,
                    e.description,
                    e.status,
                    e.created_at,
                    e.updated_at,
                    e.mro_notes
                FROM public.aircraft_maintenance_events e
                JOIN public.aircraft a ON a.id = e.aircraft_id
                WHERE {vis_sql}{extra_sql}
                ORDER BY e.created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).fetchall()

        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "aircraft_id": r.aircraft_id,
                    "tenant_id": r.created_by_tenant_id,
                    "event_type": getattr(r, "event_type", None),
                    "description": r.description,
                    "status": r.status,
                    "created_at": r.created_at,
                    "updated_at": getattr(r, "updated_at", None),
                    "mro_notes": getattr(r, "mro_notes", None),
                }
            )
        return out

    def create_event(
        self,
        *,
        aircraft_id: UUID,
        created_by_tenant_id: UUID,
        event_type: str,
        description: Optional[str],
    ) -> dict[str, Any]:
        row = self.db.execute(
            text(
                """
                INSERT INTO public.aircraft_maintenance_events
                    (id, aircraft_id, created_by_tenant_id, title, event_type, description, status)
                VALUES
                    (gen_random_uuid(), :aircraft_id, :created_by_tenant_id, :title, :event_type, :description, 'OPEN')
                RETURNING id, aircraft_id, created_by_tenant_id, event_type, description, status, created_at, updated_at, mro_notes
                """
            ),
            {
                "aircraft_id": str(aircraft_id),
                "created_by_tenant_id": str(created_by_tenant_id),
                "title": event_type,
                "event_type": event_type,
                "description": description,
            },
        ).fetchone()
        assert row is not None
        return {
            "id": row.id,
            "aircraft_id": row.aircraft_id,
            "tenant_id": row.created_by_tenant_id,
            "event_type": getattr(row, "event_type", None),
            "description": row.description,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", None),
            "mro_notes": getattr(row, "mro_notes", None),
        }

    def get_event(self, event_id: UUID) -> Optional[dict[str, Any]]:
        row = self.db.execute(
            text(
                """
                SELECT id, aircraft_id, created_by_tenant_id, event_type, description, status, created_at, updated_at, mro_notes
                FROM public.aircraft_maintenance_events
                WHERE id = :id
                """
            ),
            {"id": str(event_id)},
        ).fetchone()
        if not row:
            return None
        return {
            "id": row.id,
            "aircraft_id": row.aircraft_id,
            "tenant_id": row.created_by_tenant_id,
            "event_type": getattr(row, "event_type", None),
            "description": row.description,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", None),
            "mro_notes": getattr(row, "mro_notes", None),
        }

    def update_event_status(
        self,
        *,
        event_id: UUID,
        new_status: str,
        mro_notes: Optional[str],
    ) -> dict[str, Any]:
        row = self.db.execute(
            text(
                """
                UPDATE public.aircraft_maintenance_events
                SET status = :status,
                    mro_notes = COALESCE(:mro_notes, mro_notes),
                    updated_at = now()
                WHERE id = :id
                RETURNING id, aircraft_id, created_by_tenant_id, event_type, description, status, created_at, updated_at, mro_notes
                """
            ),
            {"id": str(event_id), "status": new_status, "mro_notes": mro_notes},
        ).fetchone()
        assert row is not None
        return {
            "id": row.id,
            "aircraft_id": row.aircraft_id,
            "tenant_id": row.created_by_tenant_id,
            "event_type": getattr(row, "event_type", None),
            "description": row.description,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", None),
            "mro_notes": getattr(row, "mro_notes", None),
        }
