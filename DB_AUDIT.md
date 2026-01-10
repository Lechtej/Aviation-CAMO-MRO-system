# DB AUDIT — v0.2.2 (public + seed) (public + seed)

## Cel etapu 1
- Dodać **publiczną warstwę danych wspólnych** (organizacje/tenanci, klienci, relacje MRO↔Airline, rejestr samolotów).
- Przygotować **nawodnienie (seed)** dla grupy **PGL** i kluczowych tenantów:
  - **LOTAMS** (MRO)
  - **LST / LS Technics** (MRO)
  - **PLL LOT / LOT** (CAMO + Airline owner)

## Najważniejsze decyzje modelu
1. **Schema-per-tenant** zostaje bez zmian dla tabel operacyjnych (inventory itd.).
2. Wspólne dane, które muszą być widoczne dla wielu tenantów (np. samoloty + relacje serwisowe), trzymamy w **public**.
3. „Klient (linia lotnicza)” jest też **tenantem** (`tenant_type='AIRLINE_CUSTOMER'`), żeby:
   - dało się przypisać mu samoloty jako `owner_tenant_id`
   - dało się robić relacje serwisowe MRO↔Customer
4. Dodano pojęcie **grupy tenantów** (`public.tenant_groups`) — na start: **PGL**.

## Pliki dodane w tej paczce
- `db/migrations/public/0001_public_tenants_aircraft.sql`
- `db/seed/seed_public_pgl_tenants_and_lot_fleet_v0.2.1.sql`

## Co jest zaimportowane (seed)
- Tenant group: **PGL**
- Tenanci PGL:
  - `lotams` (MRO)
  - `lst` (MRO)
  - `lot` (CAMO, profil airline: IATA LO / ICAO LOT)
- Tenanci-klienci (`AIRLINE_CUSTOMER`) z arkusza **Airlines** (jeśli nazwa nie mapuje się do LOT).
- Relacje `public.mro_customers` zgodnie z arkuszem **Airlines**
- Flota LOT z arkusza **Fleet_SAMPLE**: 14 rekordów `public.aircraft`
  - dostęp serwisowy (MRO access) dla **LOTAMS** i **LST** do każdego samolotu

## Jak uruchomić (psql)
1. Migracje public:
   - `psql -v ON_ERROR_STOP=1 -d aviation -U aviation -f db/migrations/public/0001_public_tenants_aircraft.sql`
2. (opcjonalnie) migracje shared/tenant jak dotychczas
3. Seed:
   - `psql -v ON_ERROR_STOP=1 -d aviation -U aviation -f db/seed/seed_public_pgl_tenants_and_lot_fleet_v0.2.1.sql`

## Uwaga o brakującej flocie
Arkusz `Fleet` w dostarczonym XLSX był pusty — wykorzystano `Fleet_SAMPLE`.
Jeśli później wypełnisz `Fleet`, przygotujemy kolejną paczkę seed v0.2.2 z pełnym importem.


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
