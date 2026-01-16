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


---

## Addendum (2026-01-16) — pitfalls observed on server

### PowerShell truncates heredocs / pasted blocks
When pasting multi-line blocks from Windows PowerShell, the content may be truncated or merged (e.g. stray `PY` tokens, duplicated decorators). **Prefer editing on the server** (nano) or use a single `cat <<'EOF'` heredoc executed on the server.

**Recommendation:** create/replace files using:

```bash
cat > <PATH> <<'EOF'
# full file content
EOF
python3 -m py_compile <PATH>
```

### `curl | head` hides failures
`echo $?` after a pipeline may not reflect `curl` failure. Use pipefail:

```bash
set -o pipefail
curl -sS http://127.0.0.1:8000/openapi.json | head -c 200; echo
echo "curl_exit=${PIPESTATUS[0]}  head_exit=${PIPESTATUS[1]}"
```

### Verify container content (bind mount vs baked image)
If you expect runtime changes without rebuild, verify `/app` content inside the container:

```bash
cd infra/docker
docker compose exec -T api sh -lc 'ls -la /app; ls -la /app/modules'
```


---

## Update #20 — Notes from live server debugging (2026-01-16)

### PowerShell truncation when pasting code (common)
Symptoms: pasted `cat <<'PY' ... PY` blocks end up **corrupted** (duplicated fragments, missing newlines, stray tokens).

Recommendation (server-side): prefer one of these patterns:
1) **nano** edit (safe for short files):
```bash
nano apps/api/src/modules/workforce/router.py
```
2) **heredoc but from bash on server**, not through PowerShell copy/paste:
```bash
cat > apps/api/src/modules/workforce/router.py <<'PY'
# ...content...
PY
```
3) Validate immediately:
```bash
python3 -m py_compile apps/api/src/modules/workforce/router.py
```

### curl pipelines: exit codes can lie without pipefail
If you pipe into `head`, `sed`, etc., `echo $?` often reports the last command, not `curl`.
Use:
```bash
set -o pipefail
curl -sS http://127.0.0.1:8000/openapi.json | head -c 200; echo
echo "curl_exit=${PIPESTATUS[0]}  head_exit=${PIPESTATUS[1]}"
```

### Dev note: container image COPY vs bind mount
If API code changes do not show up, confirm whether you are:
- running **image COPY** (`docker compose up -d --build`) OR
- running **bind mount override** (dev compose override)

Always verify what the container sees:
```bash
cd infra/docker
docker compose exec api ls -la /app | sed -n '1,40p'
```
