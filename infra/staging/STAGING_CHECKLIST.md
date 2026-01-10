# STAGING CHECKLIST — AviationCAMO-MRO

## 1. Serwer
- Linux VPS (Ubuntu 22.04 LTS lub nowszy)
- Dostęp SSH (user z sudo)
- Otwarte porty:
  - 3000 (UI)
  - 8000 (API)
  - 8080 (Keycloak)
  - 80 / 443 (future reverse proxy)

## 2. Oprogramowanie
- Docker Engine (latest stable)
- Docker Compose plugin (`docker compose`)
- curl

## 3. Katalogi (poza repo)
Utworzyć:
- `/opt/aviation-camo-mro/staging/postgres`
- `/opt/aviation-camo-mro/staging/keycloak`
- `/opt/aviation-camo-mro/staging/logs`

Uprawnienia:
- właściciel: użytkownik deployujący
- zapisywalne przez Docker

## 4. Repo
- Skopiować repo lub ZIP release
- Przejść do katalogu root systemu

## 5. Konfiguracja
- Utworzyć `.env` na podstawie:
  - `infra/staging/env.example`
- NIE commitować `.env`

## 6. Start
```bash
bash scripts/start_system.sh


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
