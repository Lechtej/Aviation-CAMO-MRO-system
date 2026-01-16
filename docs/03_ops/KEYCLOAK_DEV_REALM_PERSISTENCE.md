# Keycloak DEV — realm persistence & safe rebuilds

## Problem
In DEV, Keycloak realm (`aviation`) may **disappear** after container recreate when:
- realm was imported at startup (`--import-realm`) but
- Keycloak data directory is not persisted (no Docker volume) and container state is reinitialized, and/or
- startup flags were changed (e.g., removing `--import-realm`), resulting in a fresh instance without the realm.

This breaks OIDC for the API and UI (`Realm does not exist`).

## Target
- DEV Keycloak must persist its database across `docker compose up -d --build`.
- Realm import should be **idempotent** and used only for first boot or deliberate reset.

## Recommended docker-compose changes (DEV)
1) Persist Keycloak data:
- add volume: `/opt/keycloak/data`

2) Keep realm JSON under `/opt/keycloak/data/import` (as today).

Example snippet:
```yaml
keycloak:
  image: quay.io/keycloak/keycloak:25.0
  ports:
    - "8080:8080"
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: Admin1234!
  command:
    - start-dev
    - --import-realm
  volumes:
    - keycloak_data:/opt/keycloak/data
    - ./keycloak:/opt/keycloak/data/import

volumes:
  keycloak_data:
```

## Safe rebuild procedure
- Rebuild API/UI freely.
- Avoid deleting `keycloak_data` volume unless you intentionally want a full reset.

Commands:
```bash
cd infra/docker

docker compose up -d keycloak
# verify realm exists
curl -sS http://localhost:8080/realms/aviation/.well-known/openid-configuration | head
```

## Deliberate reset (DEV only)
If you must reset:
```bash
cd infra/docker

docker compose down
# WARNING: wipes realms/users
docker volume rm docker_keycloak_data || true

docker compose up -d keycloak
```
