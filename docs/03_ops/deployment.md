# Deployment (MVP)

Ten dokument jest **skrótowym stubem**. Docelowy opis produkcji i dostępu do serwera znajduje się tutaj:
- `docs/03_ops/SERVER_AND_DEPLOYMENT.md`

## Local
Use Docker Compose under `infra/docker/docker-compose.yml`.

## Environments
- dev (local)
- staging (overlay: `infra/staging/docker-compose.staging.yml`)
- prod (post-MVP)

## Notes
- Kubernetes support can be added post-MVP.
