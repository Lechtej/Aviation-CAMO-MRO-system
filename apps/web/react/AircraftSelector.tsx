import React, { useEffect, useMemo, useState } from "react";

export type AircraftDto = {
  id: string;
  owner_tenant_id: string;
  registration: string;
  aircraft_type: string;
  serial_number?: string | null;
  status_tech?: string | null;
  notes?: string | null;
  total_fh?: number | null;
  total_fc?: number | null;
};

export type AircraftBadge = "OWNER" | "MRO";

export type AircraftPermissions = {
  can_edit: boolean;
  can_create_events: boolean;
  can_issue_parts: boolean;
};

export type SelectedAircraftContext = {
  aircraftId: string;
  badge: AircraftBadge;
  permissions: AircraftPermissions;
};

type Props = {
  /** API base URL, e.g. https://api.forgemotionsystems.com */
  baseUrl: string;

  /** Bearer token used by API; tenant_id should be present in JWT claims OR you run as PLATFORM_ADMIN with X-Tenant-Id elsewhere */
  accessToken: string;

  /** tenant_id (UUID). Recommended: take from JWT claim tenant_id and pass in explicitly to avoid decoding in UI layer. */
  currentTenantId: string;

  /** Optional override: tenant_id (UUID) of technical UNKNOWN_OWNER tenant (code: 'unk'). If set, even when currentTenantId matches owner_tenant_id, treat as MRO-only. */
  unknownOwnerTenantId?: string;

  /** Optional: read/write aircraft_id to URL query (default: true) */
  syncToUrl?: boolean;

  /** Initial aircraft_id (e.g. from URL). If invalid or not present in list, selector stays empty. */
  initialAircraftId?: string;

  /** Fired only when user picks aircraft (no auto-select). If empty selection => null. */
  onChange?: (ctx: SelectedAircraftContext | null) => void;
};

function buildPermissions(badge: AircraftBadge): AircraftPermissions {
  // Default rules for #14.2:
  // - OWNER: full actions
  // - MRO  : read-only / no destructive
  if (badge === "OWNER") {
    return { can_edit: true, can_create_events: true, can_issue_parts: true };
  }
  return { can_edit: false, can_create_events: false, can_issue_parts: false };
}

function getBadge(params: {
  currentTenantId: string;
  ownerTenantId: string;
  unknownOwnerTenantId?: string;
}): AircraftBadge {
  const { currentTenantId, ownerTenantId, unknownOwnerTenantId } = params;

  // UNKNOWN owner: always treat as MRO-only (even if current tenant == owner)
  if (unknownOwnerTenantId && ownerTenantId === unknownOwnerTenantId) return "MRO";

  return currentTenantId === ownerTenantId ? "OWNER" : "MRO";
}

function readAircraftIdFromUrl(): string | null {
  try {
    const u = new URL(window.location.href);
    return u.searchParams.get("aircraft_id");
  } catch {
    return null;
  }
}

function writeAircraftIdToUrl(aircraftId: string | null) {
  const u = new URL(window.location.href);
  if (!aircraftId) u.searchParams.delete("aircraft_id");
  else u.searchParams.set("aircraft_id", aircraftId);
  // preserve hash-based routing
  window.history.replaceState({}, "", u.toString());
}

export function AircraftSelector(props: Props) {
  const {
    baseUrl,
    accessToken,
    currentTenantId,
    unknownOwnerTenantId,
    syncToUrl = true,
    initialAircraftId,
    onChange,
  } = props;

  const [aircraft, setAircraft] = useState<AircraftDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initialFromUrl = useMemo(() => (syncToUrl ? readAircraftIdFromUrl() : null), [syncToUrl]);

  // IMPORTANT: no auto-selection.
  const [selectedId, setSelectedId] = useState<string | "">(
    (initialAircraftId || initialFromUrl || "")
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const r = await fetch(baseUrl.replace(/\/+$/, "") + "/v1/aircraft", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
        });
        if (!r.ok) {
          const t = await r.text();
          throw new Error(`${r.status} ${r.statusText}: ${t}`);
        }
        const data = (await r.json()) as AircraftDto[];
        if (!cancelled) setAircraft(Array.isArray(data) ? data : []);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [baseUrl, accessToken]);

  const selected = useMemo(() => {
    if (!selectedId) return null;
    return aircraft.find((a) => a.id === selectedId) || null;
  }, [aircraft, selectedId]);

  const selectedCtx = useMemo<SelectedAircraftContext | null>(() => {
    if (!selected) return null;
    const badge = getBadge({
      currentTenantId,
      ownerTenantId: selected.owner_tenant_id,
      unknownOwnerTenantId,
    });
    return {
      aircraftId: selected.id,
      badge,
      permissions: buildPermissions(badge),
    };
  }, [selected, currentTenantId, unknownOwnerTenantId]);

  useEffect(() => {
    // URL sync is optional and should not cause auto-selection.
    if (syncToUrl) writeAircraftIdToUrl(selectedId ? selectedId : null);
    onChange?.(selectedCtx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
      <label style={{ fontSize: 12, opacity: 0.8 }}>Aircraft</label>

      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        style={{
          height: 34,
          borderRadius: 10,
          padding: "0 10px",
          minWidth: 320,
        }}
      >
        <option value="">— wybierz aircraft —</option>
        {aircraft.map((a) => {
          const badge = getBadge({
            currentTenantId,
            ownerTenantId: a.owner_tenant_id,
            unknownOwnerTenantId,
          });
          const badgeLabel = badge === "OWNER" ? "OWNER" : "MRO";
          return (
            <option key={a.id} value={a.id}>
              {a.registration} · {a.aircraft_type} · {badgeLabel}
            </option>
          );
        })}
      </select>

      {loading && <span style={{ fontSize: 12, opacity: 0.8 }}>loading…</span>}
      {error && <span style={{ fontSize: 12, color: "#ff6b6b" }}>{error}</span>}

      {selectedCtx && (
        <span style={{ fontSize: 12, opacity: 0.85 }}>
          ctx: {selectedCtx.badge} | edit:{selectedCtx.permissions.can_edit ? "Y" : "N"} | events:{selectedCtx.permissions.can_create_events ? "Y" : "N"} | issue:{selectedCtx.permissions.can_issue_parts ? "Y" : "N"}
        </span>
      )}
    </div>
  );
}
