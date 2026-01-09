# Server: Auth + tenant bootstrap (Keycloak + API)


## STATUS FREEZE (2026-01-09) – Local dev closure (Keycloak + API + RBAC DB)

### What was fixed
- API `GET /v1/tenants` was failing with **500** due to missing RBAC tables: `public.auth_permissions` (and related).
- Applied DB migration + seeds:
  - `db/migrations/public/0003_public_auth_rbac.sql`
  - `db/seed/seed_public_auth_rbac_catalog_v0.2.4.sql`
  - `db/seed/seed_public_auth_rbac_kc_bridge_v0.2.4.sql`

### Verified outcomes (evidence)
- API: `GET http://localhost:8000/health` → **200** `{"status":"ok"}`
- Token issuance (example users):
  - `test_platform_admin` → role includes `PLATFORM_ADMIN`
  - `test_auditor` → role includes `AUDITOR`
- API call with bearer token:
  - `GET http://localhost:8000/v1/tenants` → **200** `[]`
- DB RBAC objects exist and are populated:
  - tables: `public.auth_roles`, `public.auth_permissions`, `public.auth_role_permissions`
  - counts: roles **68**, permissions **71**, mappings **619**

### PowerShell helpers (recommended)
```powershell
function Get-KcToken {
  param(
    [string]$KC = "http://localhost:8080",
    [string]$Realm = "aviation",
    [string]$ClientId = "aviation-api",
    [string]$User,
    [string]$Pass
  )

  $resp = curl.exe -s -X POST "$KC/realms/$Realm/protocol/openid-connect/token" `
    -H "Content-Type: application/x-www-form-urlencoded" `
    -d "grant_type=password" `
    -d "client_id=$ClientId" `
    -d "username=$User" `
    -d "password=$Pass"

  $tok = ($resp | ConvertFrom-Json).access_token
  if (-not $tok -or $tok.Length -eq 0) { throw "TOKEN_EMPTY" }
  return $tok
}

$TOKEN = Get-KcToken -User "test_auditor" -Pass "Test1234!"
curl.exe -i -s --max-time 10 "http://localhost:8000/v1/tenants" -H "Authorization: Bearer $TOKEN"
```

### Common pitfall
- Running commands from `C:\WINDOWS\system32` breaks relative paths (e.g., compose file). Always `cd` to repo root before `docker compose ...`.

> Scope: **Ubuntu host** running Docker Compose from `infra/docker/`.
>
> Goal: run end-to-end calls with **client_credentials** token + **tenant context**.

## 0) Quick health checks

```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

docker compose ps
curl -sS http://127.0.0.1:8000/health; echo
curl -sSI http://127.0.0.1:8000/docs | head -n 5
curl -sS http://127.0.0.1:8080/realms/aviation/.well-known/openid-configuration | head -c 200; echo
```

Expected:
- API `/health` returns `{"status":"ok"}`
- Keycloak well-known config returns JSON with an `issuer`.

## 1) Confirm API OIDC env (compose)

On the host:

```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

docker compose config | grep -E "OIDC_ISSUER|OIDC_JWKS_URL"
```

Validated dev server mapping:
- `OIDC_ISSUER` points to the **host-mapped** Keycloak URL (so it matches the `iss` in tokens you obtain from the host):
  - `http://127.0.0.1:8080/realms/aviation`
- `OIDC_JWKS_URL` points to a URL reachable from **inside the API container**:
  - `http://keycloak:8080/realms/aviation/protocol/openid-connect/certs`

## 2) Ensure Keycloak realms allow HTTP (`sslRequired: none`)

```bash
# show current values
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master --fields sslRequired
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/aviation --fields sslRequired
```

If needed (apply once):

```bash
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh update realms/aviation -s sslRequired=none
```

Re-check:

```bash
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/master --fields sslRequired
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/aviation --fields sslRequired
```

## 3) Turn `aviation-api` into a confidential client (service account) and get secret

Find client ID (Keycloak internal UUID) and enable service account:

```bash
CID=$(docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get clients -r aviation -q clientId=aviation-api --fields id --format csv \
  | tail -n 1 | tr -d '\r' | tr -d '"')

echo "CID=$CID"

docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh update clients/$CID -r aviation \
  -s serviceAccountsEnabled=true -s publicClient=false
```

Read client secret:

```bash
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get clients/$CID/client-secret -r aviation
```

Store it in your shell for the next steps:

```bash
SECRET="<paste_value_here>"
```

## 4) Grant `PLATFORM_ADMIN` to the service account user

Confirm role exists:

```bash
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get roles -r aviation | grep -n '"name" : "PLATFORM_ADMIN"' || true
```

Resolve service-account user UUID and add role:

```bash
SA_UID=$(docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get clients/$CID/service-account-user -r aviation --fields id --format csv \
  | tail -n 1 | tr -d '\r' | tr -d '"')

echo "SA_UID=$SA_UID"

docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh add-roles -r aviation --uid "$SA_UID" --rolename PLATFORM_ADMIN

# verify mapping
docker exec -it docker-keycloak-1 /opt/keycloak/bin/kcadm.sh get users/$SA_UID/role-mappings/realm -r aviation | grep -n PLATFORM_ADMIN || true
```

## 5) Obtain an access token on the host (client_credentials)

**Important:** access tokens are short-lived (commonly ~300 seconds). Obtain a fresh token before admin/test calls.

```bash
TOKEN=$(curl -sS -X POST "http://127.0.0.1:8080/realms/aviation/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=aviation-api" \
  --data-urlencode "client_secret=${SECRET}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "TOKEN_LEN=${#TOKEN}"
```

Optional: validate claims quickly (should include `PLATFORM_ADMIN` in realm roles):

```bash
export TOKEN
python3 - <<'PY'
import os, json, base64
parts=os.environ['TOKEN'].split('.')
payload = parts[1] + '=='
claims=json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
print('iss:', claims.get('iss'))
print('azp:', claims.get('azp'))
print('realm_access.roles:', (claims.get('realm_access') or {}).get('roles'))
PY
```

## 6) Create / find a tenant and use `X-Tenant-Id`

List tenants:

```bash
curl -sS http://127.0.0.1:8000/v1/tenants -H "Authorization: Bearer ${TOKEN}"; echo
```

If you need a demo tenant:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/tenants \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"code":"DEMO","name":"Demo Airline"}'
```

Capture tenant ID:

```bash
TENANT_ID=$(curl -sS http://127.0.0.1:8000/v1/tenants \
  -H "Authorization: Bearer ${TOKEN}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["id"])')

echo "TENANT_ID=$TENANT_ID"
```

For tenant-scoped endpoints, always send:

```bash
-H "X-Tenant-Id: ${TENANT_ID}"
```

## 7) Bootstrap logistics for the tenant

```bash
curl -sS -i -X POST http://127.0.0.1:8000/v1/logistics/_admin/bootstrap \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Verify UOM exists:

```bash
curl -sS http://127.0.0.1:8000/v1/logistics/uom \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}"; echo
```

## 8) Minimal demo data (tenant)

### 8.1 Create a Part

```bash
PART=$(curl -sS -X POST http://127.0.0.1:8000/v1/inventory/parts \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "part_number": "PN-0001",
    "part_type": "CONSUMABLE",
    "is_pool_item": false,
    "uom_code": "EA",
    "description": "Test part PN-0001"
  }')

echo "$PART" | head -c 200; echo

PART_ID=$(echo "$PART" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "PART_ID=$PART_ID"
```

### 8.2 Create a Warehouse

```bash
WH=$(curl -sS -X POST http://127.0.0.1:8000/v1/logistics/warehouses \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"code":"WH1","name":"Main Warehouse"}')

echo "$WH"; echo
WAREHOUSE_ID=$(echo "$WH" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "WAREHOUSE_ID=$WAREHOUSE_ID"
```

### 8.3 Create a Location (bin) inside warehouse

```bash
LOC=$(curl -sS -X POST http://127.0.0.1:8000/v1/logistics/locations \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"warehouse_id\":\"${WAREHOUSE_ID}\",\"code\":\"BIN-A1\",\"name\":\"Bin A1\"}")

echo "$LOC"; echo
LOCATION_ID=$(echo "$LOC" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "LOCATION_ID=$LOCATION_ID"
```

### 8.4 Create a Stock Item (inventory item)

```bash
INV=$(curl -sS -X POST http://127.0.0.1:8000/v1/logistics/stock-items \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"part_id\":\"${PART_ID}\",\"location_id\":\"${LOCATION_ID}\"}")

echo "$INV"; echo
INV_ID=$(echo "$INV" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "INV_ID=$INV_ID"
```

## 9) Movements endpoint

The OpenAPI spec includes `POST /v1/logistics/movements`, however in server validation runs this call returned **404 Not Found**.

To reproduce with a fresh token:

```bash
curl -sS -i -X POST http://127.0.0.1:8000/v1/logistics/movements \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -H "Content-Type: application/json" \
  -d "{\"inventory_item_id\":\"${INV_ID}\",\"movement_type\":\"RECEIPT\",\"quantity\":10}" \
  | head -n 80
```

If it returns `Invalid token: Signature has expired`, re-run the token acquisition step.

If it returns `404 Not Found`:
- confirm the path exists in the running API spec: `curl -sS http://127.0.0.1:8000/openapi.json | grep -n '"/v1/logistics/movements"'`
- check API logs: `docker logs docker-api-1 --tail=200`
- this may indicate the route is present in OpenAPI but the router is not mounted, feature-flagged, or pending implementation.
