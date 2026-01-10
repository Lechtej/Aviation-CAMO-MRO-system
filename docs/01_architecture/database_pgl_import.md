# Database PGL Import (Server)

## Cel
Import datasetu PGL (airlines, aircraft, MRO access) do bazy Postgres na serwerze (schema `public` – układ produkcyjny).

## Pliki
- `db/import/scripts/load_from_csv_server.sql` – właściwy import (server schema)
- `db/import/scripts/verify_import_server.sql` – weryfikacja po imporcie

## Założenia
- Stack działa na serwerze pod Docker Compose.
- CSV znajdują się w kontenerze DB pod `/tmp/import_staging/`:
  - `airline_customers.csv`
  - `mro_customers.csv`
  - `aircraft.csv`
  - `aircraft_mro_access.csv`

## Procedura (serwer)
1) Wejście na serwer:
```bash
ssh root@65.108.250.169
```

2) Przejdź do compose:
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker
```

3) Skopiuj CSV do kontenera DB (wariant A – z hosta serwera):
```bash
docker cp /tmp/import_staging/. docker-db-1:/tmp/import_staging
```

4) Uruchom import:
```bash
docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -f db/import/scripts/load_from_csv_server.sql
```

5) Uruchom weryfikację:
```bash
docker compose exec -T db psql -U aviation -d aviation -v ON_ERROR_STOP=1 -f db/import/scripts/verify_import_server.sql
```

## Oczekiwane rezultaty (przykład)
- `aircraft` oraz `aircraft_mro_access` mają tę samą liczność (dla tego datasetu).
- `orphan_access = 0`
- brak pustych `registration` / `current_registration` (zależnie od schematu)


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
