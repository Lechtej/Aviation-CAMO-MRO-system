# DR / Backup Plan (minimal)

## Cel
Odtworzyć środowisko (local lub server-dev) po awarii dostawcy bez kopiowania „całego systemu”.

## Co backupujemy (stateful)
1) **Postgres (db dump)** — dane aplikacyjne.
2) **Keycloak realm export** — konfiguracja realm + klienci + role + (opcjonalnie) użytkownicy testowe.

## Czego nie backupujemy w repo
- `.env.*` (sekrety)
- certyfikaty prywatne
- dane produkcyjne „na żywo” bez kontroli

## Gdzie trzymamy
- Lokalnie (dysk + kopia na inny nośnik)
- Offsite (S3/Backblaze/Drive) — szyfrowane archiwum

## Procedury (manual MVP)
### 1) DB dump (server-dev)
W katalogu `infra/docker`:
- dump:
  - `docker compose exec -T db pg_dump -U postgres -d aviationcamo > backups/db_YYYYMMDD.sql`
- restore:
  - `cat backups/db_YYYYMMDD.sql | docker compose exec -T db psql -U postgres -d aviationcamo`

*(Nazwy `-U`, `-d` dopasować do realnych env vars w compose.)*

### 2) Keycloak realm export
- export realm do pliku:
  - `docker compose exec -T keycloak /opt/keycloak/bin/kc.sh export --file /tmp/realm-export.json --realm aviation`
- skopiuj z kontenera:
  - `docker cp docker-keycloak-1:/tmp/realm-export.json backups/realm_aviation_YYYYMMDD.json`

## Outage recovery checklist (local-first)
1) `docker compose up -d` na local
2) `scripts/bootstrap_local.sh` (seed + minimalny tenant/user)
3) `scripts/smoke_auth.sh` → token
4) `scripts/smoke_api.sh` → `/v1/roles=200`, `/v1/tenants=200`
5) Dopiero potem: reconcile server-dev po powrocie dostępności

