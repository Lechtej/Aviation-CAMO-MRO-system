# #14.8 — UI: Aircraft list + selector alignment (follow-up)

## Stan wejściowy (PASS/FAIL)

PASS
- `apps/web/app.js` — składnia poprawna (`node --check` RC=0).
- UI startuje, nawigacja działa.
- LocalStorage zawiera `tenant_uuid`, `tenant_schema` i auth (`aviationcamo_auth_v1`).

FAIL (problem)
- `/camo/aircraft`: brak listy/filtrów aircraft; samoloty nie ładują się.
- Selector aircraft widoczny w Maintenance, ale nie w Aircraft.

## Fakty z obserwacji (DevTools)
- Brak call do `/v1/tenants` jest **oczekiwany**, jeśli `tenant_uuid` już istnieje w LocalStorage.
- Problem nie jest już „storm/init” ani „syntax error” — to teraz czysto: **UI route/layout + fetch/render**.

## Cel wątku #14.8 (jednoznaczny)

1. **Aircraft view** (`/camo/aircraft`):
   - lista wszystkich aircraft dostępnych w tenant (wg RBAC),
   - filtr/szukajka (min. po registration/type),
   - klik → ustawienie `aircraft_id` w kontekście.

2. **Maintenance view** (`/camo/maintenance-events`):
   - ten sam selector (shared component / shared logic),
   - filtrowanie listy Maintenance Events po wybranym `aircraft_id`.

## RBAC / widoczność (wymagania)
- PLL LOT (CAMO): widzi **swoje** aircraft.
- LOTAMS / LST / MRO: widzi aircraft swoich klientów (tenant-scope + role).

## Pytania kontrolne (na start)
- Czy `/v1/aircraft` ma zwracać pełną listę (tenant-scope), czy paginowaną?
- Jaki minimalny zestaw pól jest potrzebny do listy/filtra (np. `id`, `registration`, `aircraft_type`, `owner_*`)?
