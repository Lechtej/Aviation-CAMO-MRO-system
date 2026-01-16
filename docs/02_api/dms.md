# API — DMS (Draft Contract)

> This is a draft contract for the DMS module. It defines MVP endpoints and invariants.

## Principles
- Every call is tenant-scoped.
- Documents are append-only; no hard delete.
- Lifecycle transitions are validated and audited.

## Endpoints (v1)
### Types
- `GET /v1/dms/types` — list document types (registry)

### Documents
- `GET /v1/dms/documents` — list (filters: type/status/domain/related entity)
- `POST /v1/dms/documents` — create DRAFT
- `GET /v1/dms/documents/{id}` — details
- `PATCH /v1/dms/documents/{id}` — update metadata (only when editable)

### Lifecycle
- `POST /v1/dms/documents/{id}/approve`
- `POST /v1/dms/documents/{id}/issue`
- `POST /v1/dms/documents/{id}/sign`
- `POST /v1/dms/documents/{id}/archive`

### Attachments
- `POST /v1/dms/documents/{id}/attachments` — upload
- `GET /v1/dms/attachments/{id}` — download (RBAC + tenant)

### Rendering / printing
- `POST /v1/dms/documents/{id}/render` — generate PDF artifact (template-versioned)
- `GET /v1/dms/documents/{id}/pdf` — fetch latest rendered PDF

## Core invariants
- `immutable_after` enforced per type.
- Archived documents are immutable and reproducible.
- Every lifecycle transition is persisted as an audit event.


## Auth / OIDC runtime requirements (DEV & PROD)
DMS endpoints are protected by the same OIDC middleware as other modules.
Two invariants are critical for stable DEV:

1) **Issuer match**
- `OIDC_ISSUER` must match the `iss` claim in JWT.
- Example (DEV docker): `http://keycloak:8080/realms/aviation` is safer for container-to-container consistency.

2) **JWKS reachability from API container**
- `OIDC_JWKS_URL` must be reachable **from inside the api container**.
- Use Keycloak service DNS name on the docker network: `http://keycloak:8080/.../certs`.

### Quick verification (inside api container)
```sh
# show runtime config
env | grep -E "OIDC_ISSUER|OIDC_JWKS_URL"

# JWKS should return HTTP 200
python3 - <<'PY'
import os, urllib.request
url=os.environ.get('OIDC_JWKS_URL')
with urllib.request.urlopen(url, timeout=5) as r:
    print('HTTP', r.status)
PY
```

## Troubleshooting map (most common)
- `Missing bearer token` → request missing `Authorization: Bearer <token>` or token extraction failed (empty var).
- `Invalid token: Invalid issuer` → `OIDC_ISSUER` differs from JWT `iss`.
- `Fail to fetch data from the url` → API cannot reach JWKS URL (bad hostname or network).

## Auth / OIDC requirements (DEV + PROD)
The API validates tokens by verifying:
- JWT signature against JWKS
- `iss` (issuer) matches configured `OIDC_ISSUER`

### Practical rule
`OIDC_ISSUER` **must equal** the token claim `iss`.
Example (docker-compose on single host):
- token `iss`: `http://localhost:8080/realms/aviation`
- API `OIDC_ISSUER`: `http://localhost:8080/realms/aviation`

`OIDC_JWKS_URL` must be reachable **from inside the API container**.
Recommended: use the Docker service name:
- `OIDC_JWKS_URL=http://keycloak:8080/realms/aviation/protocol/openid-connect/certs`

### Troubleshooting checklist
1. **401 Missing bearer token** → request has no `Authorization: Bearer <JWT>` header.
2. **Invalid token: Invalid issuer** → `OIDC_ISSUER` mismatch vs token `iss`.
3. **Fail to fetch data from the url / Connection refused** → API cannot reach JWKS URL.

Minimal in-container connectivity test:
```sh
docker compose exec -T api python3 - <<'PY'
import os, urllib.request
url=os.environ.get('OIDC_JWKS_URL')
print('JWKS_URL=', url)
with urllib.request.urlopen(url, timeout=5) as r:
    print('HTTP', r.status, 'len', len(r.read()))
PY
```


---

## ADDENDUM 2026-01-16 — DMS review pass (docs hardening)

### Tenant context (MVP)
DMS is **always tenant-scoped**. The middleware must resolve tenant context **before** routing.
Accepted resolution order (align with `docs/02_api/TENANT_CONTEXT.md`):
1. `X-Tenant-Id` (override; PLATFORM_ADMIN only)
2. JWT claim `tenant_id` (target PROD)
3. `X-Debug-Tenant-Id` only when `DEBUG_TENANT_HEADER=true` (DEV)

### Minimal RBAC (MVP)
- `GET /v1/dms/types` and `GET /v1/dms/documents*` require authenticated user with tenant access.
- Lifecycle actions (`approve/issue/sign/archive`) require roles allowed by document type registry (`allowed_roles`).

### Smoke test (post-auth-stabilization)
Run after Keycloak DEV persistence is confirmed.

```bash
# 1) obtain token (example; adjust to your scripts)
TOKEN=$(./get_token_dev.sh)

# 2) types
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <TENANT_UUID>"   http://localhost:8000/v1/dms/types | jq .

# 3) documents list
curl -sS -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <TENANT_UUID>"   http://localhost:8000/v1/dms/documents | jq .
```

### Note (documentation hygiene)
This file contains duplicated Auth/OIDC troubleshooting content preserved for history.
Canonical section is the **first** "Auth / OIDC runtime requirements" block; future edits should extend it rather than adding new duplicates.
