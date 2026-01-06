# AviationCAMO-MRO v0.2.30 — Release Notes

## Zmiany funkcjonalne
- **Aircraft: własność + dostęp MRO**
  - Nowe endpointy `/v1/aircraft`:
    - Owner tenant może tworzyć i usuwać samoloty.
    - Owner tenant może nadawać/odbierać dostęp MRO (`/mro-access`).
    - Tenant MRO widzi przypisane samoloty i może aktualizować tylko **status_tech** i **notes**.

## Zmiany techniczne
- Dodano tabele w `public`:
  - `public.aircraft`
  - `public.aircraft_mro_access`
- Dodano dev bootstrap: `POST /v1/aircraft/_admin/bootstrap`.

## Zgodność / kompatybilność
- Zmiany są addytywne (bez migracji istniejących danych).
- Wersja jest przygotowana pod późniejsze, formalne migracje.