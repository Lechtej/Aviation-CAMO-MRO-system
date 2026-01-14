# AircraftSelector (React) — skeleton for thread #14.2

## Założenia (twarde)
- **Brak auto-wyboru** — komponent nigdy nie ustawia sam aircraft (puste pole startowe, chyba że podasz `initialAircraftId` lub `?aircraft_id=` w URL).
- Źródło danych: `GET /v1/aircraft`.
- Badge:
  - `OWNER` gdy `currentTenantId === owner_tenant_id`.
  - `MRO` w przeciwnym razie.
  - `UNKNOWN_OWNER` (tenant `unk`) można wymusić parametrem `unknownOwnerTenantId` ⇒ zawsze `MRO`.
- Permissions (flagi UI):
  - `OWNER` ⇒ `can_edit/can_create_events/can_issue_parts = true`
  - `MRO`   ⇒ wszystko `false`

## Integracja (docelowo)
1. Aplikacja trzyma **AircraftContext** w globalnym store (np. React Context / Zustand / Redux):
   - `aircraftId`
   - `badge`
   - `permissions`
2. Widoki zależne (Maintenance Events, Utilization, Parts Issue) biorą `aircraftId` z kontekstu i:
   - pokazują placeholder, gdy brak wyboru,
   - wykonują refetch przy zmianie.

## Minimalne użycie
```tsx
<AircraftSelector
  baseUrl={API_BASE_URL}
  accessToken={token}
  currentTenantId={tenantId}
  unknownOwnerTenantId={UNKNOWN_OWNER_TENANT_ID} // optional
  syncToUrl={true}
  onChange={(ctx) => setAircraftContext(ctx)}
/>
```
