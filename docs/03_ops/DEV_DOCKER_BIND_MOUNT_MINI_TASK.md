# DEV-only bind-mount for API code (mini-task)

## Context
The backend `api` container ships code into the image at build time (`infra/docker/api.Dockerfile` uses `COPY apps/api/src/ /app/`).
In DEV, host-side code changes are NOT visible until the image is rebuilt.

This mini-task introduces a DEV-only bind-mount so `apps/api/src` is mounted into `/app` at runtime.

## Non-negotiable rule
This must be DEV-only. Production compose must remain image-based (no source mounts).

## Implementation option A (recommended): compose override file
Create a new file:

- `infra/docker/docker-compose.dev.yml`

Content (only the relevant delta):

```yaml
services:
  api:
    volumes:
      - ../../apps/api/src:/app
      - ../../docs/02_api/openapi.yaml:/app/openapi.yaml:ro
    environment:
      # optional: if you add hot-reload later
      # UVICORN_RELOAD: "true"
      # WARNING: keep DEBUG_TENANT_HEADER controlled separately
      DEBUG_TENANT_HEADER: "true"
```

Start DEV stack with override:

```bash
cd infra/docker
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

PASS:
- editing a python file under `apps/api/src` changes runtime behavior without `docker compose build api`.

FAIL:
- no behavior change (mount path wrong) or container crashloop.

## Implementation option B: compose profiles
If you prefer profiles, add a profile `dev` for the volumes section and run with `--profile dev`.
This is more invasive in the base compose file and is easier to accidentally deploy to production, so option A is safer.

## Verification checklist
From server:

1) confirm mount exists:
```bash
cd infra/docker
docker compose exec api ls -la /app | sed -n '1,30p'
```

2) quick code change probe (manual):
- add a harmless log line or a temporary version string in an endpoint
- call the endpoint and confirm the change appears

3) smoke test auth unaffected:
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system
TOKEN="$(./get_token_dev.sh)"
curl -sS -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" https://api.forgemotionsystems.com/v1/roles
```

## Rollback
To rollback, stop using the override file and restart with base compose only:

```bash
cd infra/docker
docker compose down
docker compose up -d --build
```

