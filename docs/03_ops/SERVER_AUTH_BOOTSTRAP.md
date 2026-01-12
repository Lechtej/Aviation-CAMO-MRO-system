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


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---

## Update 2026-01-11 – DEV: dummy users, wspólne hasło, „Account is not fully set up”, oraz bootstrap danych

### Cel
1) Ustawić jedno startowe hasło dla dummy userów na DEV (np. `Camo1234!@`).  
2) Naprawić błąd token endpoint: `invalid_grant / Account is not fully set up` (wymuszone required actions / brak profilu).  
3) Zrobić szybki smoke test RBAC na realnych tokenach użytkowników.  
4) Nadać `PLATFORM_ADMIN` użytkownikowi CAMO i wykonać bootstrappy `_admin`.

### A. Ujednolicone hasło dla dummy userów (DEV only)
> Ryzyko: jedno wspólne hasło jest OK tylko na DEV/test. Na prod: unikalne hasła + brak Direct Access Grants.

Uruchom w katalogu docker (na serwerze):
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker
KC="http://localhost:8080"
REALM="aviation"
NEWPASS='Camo1234!@'

# login kcadm (w kontenerze)
docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh config credentials   --server "$KC" --realm master --user admin --password admin

# ustaw hasło dla wybranych userów
for U in camo_lot mro_lotams mro_lst stores_lotams; do
  echo "== set-password $U =="
  docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh set-password     -r "$REALM" --username "$U" --new-password "$NEWPASS"
done
```

### B. Naprawa `Account is not fully set up` (requiredActions + profil)
Symptom: token endpoint zwraca:
```json
{"error":"invalid_grant","error_description":"Account is not fully set up"}
```

W praktyce na DEV pomogły 2 rzeczy:
- wyczyszczenie `requiredActions` i ustawienie `enabled=true`, `emailVerified=true`,
- uzupełnienie minimalnego profilu: `email`, `firstName`, `lastName`.

**Uwaga:** w bash istnieje zmienna `UID` (readonly). Nie używaj `UID=...`; stosuj np. `USER_ID`.

```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker
KC="http://localhost:8080"
REALM="aviation"

ADMIN_TOKEN=$(curl -sS -X POST "$KC/realms/master/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=admin-cli" -d "username=admin" -d "password=admin" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

patch_user () {
  local USERNAME="$1"
  local EMAIL="$2"
  local FIRST="$3"
  local LAST="$4"

  local USER_ID
  USER_ID=$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN"     "$KC/admin/realms/$REALM/users?username=$USERNAME"   | python3 -c 'import sys,json; a=json.load(sys.stdin); print(a[0]["id"] if a else "")')

  test -n "$USER_ID" || { echo "FAIL: user not found: $USERNAME"; return 1; }

  echo "== patch $USERNAME ($USER_ID) =="
  curl -sS -o /dev/null -w "$USERNAME: http %{http_code}
"     -X PUT "$KC/admin/realms/$REALM/users/$USER_ID"     -H "Authorization: Bearer $ADMIN_TOKEN"     -H "Content-Type: application/json"     --data-binary "{"enabled":true,"emailVerified":true,"requiredActions":[],"email":"$EMAIL","firstName":"$FIRST","lastName":"$LAST"}"
}

patch_user mro_lotams   "mro_lotams@forgemotionsystems.local"   "MRO"    "LOTAMS"
patch_user mro_lst     "mro_lst@forgemotionsystems.local"      "MRO"    "LST"
patch_user stores_lotams "stores_lotams@forgemotionsystems.local" "STORES" "LOTAMS"
```

### C. Smoke test: token + roles + tenant_id
```bash
KC="http://localhost:8080"
REALM="aviation"
CLIENT_ID="aviation-api"
PASS='Camo1234!@'

for USER in mro_lotams mro_lst stores_lotams; do
  echo "===== $USER ====="
  curl -sS -o /tmp/token.json -X POST "$KC/realms/$REALM/protocol/openid-connect/token"     -H "Content-Type: application/x-www-form-urlencoded"     -d "grant_type=password" -d "client_id=$CLIENT_ID" -d "username=$USER" -d "password=$PASS"

  python3 - <<'PY'
import json, base64
o=json.load(open("/tmp/token.json"))
t=o["access_token"]
p=t.split(".")[1]; p += "=" * (-len(p)%4)
payload=json.loads(base64.urlsafe_b64decode(p.encode()))
print("tenant_id:", payload.get("tenant_id"))
print("preferred_username:", payload.get("preferred_username"))
print("roles:", (payload.get("realm_access") or {}).get("roles"))
PY
done
```

### D. `PLATFORM_ADMIN` → CAMO user + bootstrappy `_admin`
`/_admin/bootstrap` jest celowo ograniczone do `PLATFORM_ADMIN` (ochrona danych inicjalnych).

1) pobierz JSON roli:
```bash
KC="http://localhost:8080"
REALM="aviation"

ADMIN_TOKEN=$(curl -sS -X POST "$KC/realms/master/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=admin-cli" -d "username=admin" -d "password=admin" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -sS -H "Authorization: Bearer $ADMIN_TOKEN"   "$KC/admin/realms/$REALM/roles/PLATFORM_ADMIN"   -o /tmp/role_platform_admin.json
```

2) przypisz rolę `PLATFORM_ADMIN` do `camo_lot`:
```bash
KC="http://localhost:8080"
REALM="aviation"
USERNAME="camo_lot"

ADMIN_TOKEN=$(curl -sS -X POST "$KC/realms/master/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=admin-cli" -d "username=admin" -d "password=admin" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

USER_ID=$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN"   "$KC/admin/realms/$REALM/users?username=$USERNAME" | python3 -c 'import sys,json; a=json.load(sys.stdin); print(a[0]["id"] if a else "")')

ROLE_JSON=$(cat /tmp/role_platform_admin.json)

curl -sS -o /dev/null -w "assign PLATFORM_ADMIN -> $USERNAME: http %{http_code}
"   -X POST "$KC/admin/realms/$REALM/users/$USER_ID/role-mappings/realm"   -H "Authorization: Bearer $ADMIN_TOKEN"   -H "Content-Type: application/json"   --data-binary "[$ROLE_JSON]"
```

3) weryfikacja roli:
```bash
curl -sS -H "Authorization: Bearer $ADMIN_TOKEN"   "$KC/admin/realms/$REALM/users/$USER_ID/role-mappings/realm"   -o /tmp/camo_lot_realm_roles.json

python3 - <<'PY'
import json
a=json.load(open("/tmp/camo_lot_realm_roles.json","r",encoding="utf-8"))
names=sorted([x.get("name") for x in a if x.get("name")])
print("roles:", names)
print("has_PLATFORM_ADMIN:", "PLATFORM_ADMIN" in names)
PY
```

4) bootstrappy w API (po stronie tenant context, z tokenem `camo_lot`):
```bash
ISSUER="https://auth.forgemotionsystems.com/realms/aviation"
API="https://api.forgemotionsystems.com"
CLIENT_ID="aviation-api"
USER="camo_lot"
PASS='Camo1234!@'

curl -sS -o /tmp/token.json -X POST "$ISSUER/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=$CLIENT_ID" -d "username=$USER" -d "password=$PASS"

TOKEN=$(python3 -c 'import json; print(json.load(open("/tmp/token.json"))["access_token"])')

curl -sS -i -H "Authorization: Bearer $TOKEN" -X POST   "$API/v1/aircraft/_admin/bootstrap" | sed -n '1,40p'

curl -sS -i -H "Authorization: Bearer $TOKEN" -X POST   "$API/v1/logistics/_admin/bootstrap" | sed -n '1,40p'
```

### E. Minimalny test funkcjonalny: Create + List aircraft (CAMO)
```bash
API="https://api.forgemotionsystems.com"
curl -sS -i   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   -X POST "$API/v1/aircraft"   --data-binary '{"registration":"SP-TEST1"}' | sed -n '1,40p'

curl -sS -H "Authorization: Bearer $TOKEN"   "$API/v1/aircraft" | head -c 800; echo
```

### F. Wnioski (na DEV)
- `/v1/aircraft` = **CAMO-only** (403 dla MRO/STORES jest poprawne).  
- `_admin/bootstrap` = **PLATFORM_ADMIN-only**.  
- `Account is not fully set up` → naprawione przez reset required actions + profil usera.

## Fix: `invalid_grant` / `Account is not fully set up` for Password Grant (Direct Grant) — PROD-ready workaround

**Symptom**
- Token request (`grant_type=password`) returns:
  - `{"error":"invalid_grant","error_description":"Account is not fully set up"}`

**Root cause (observed)**
- Realm has **Direct Grant** flow requiring OTP and/or profile verification actions.
- Some **Required Actions** are enabled (even if not set on user), which blocks direct grant in this environment.

**Target state (MVP / testing)**
- Realm `directGrantFlow` points to a cloned flow with OTP disabled.
- Required Actions that can block direct grant are disabled.

> Note: this is **not** a security recommendation for production user-facing login. This is a pragmatic unblocker for service/UI testing in this project setup.

### Commands (server-side)

```bash
# 0) SSH + go to compose dir
ssh root@<SERVER_IP>
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

KCADM="/opt/keycloak/bin/kcadm.sh"

# 1) admin login for kcadm (session can expire)
docker compose exec -T keycloak $KCADM config credentials   --server http://localhost:8080   --realm master   --user admin   --password 'admin123!'

# 2) create (or reuse) a copy of built-in "direct grant" flow
DG="direct%20grant"
NEW="direct-grant-no-otp"

# if it already exists -> Keycloak returns "New flow alias name already exists" (safe to ignore)
docker compose exec -T keycloak $KCADM create "authentication/flows/$DG/copy" -r aviation -s "newName=$NEW" || true

# 3) verify the executions in the new flow: OTP + condition must be DISABLED
docker compose exec -T keycloak $KCADM get "authentication/flows/$NEW/executions" -r aviation   | egrep -n '"displayName"|"providerId"|"requirement"' -n

# EXPECT (important lines):
# - Condition - user configured -> DISABLED
# - OTP -> DISABLED
# - Username Validation -> REQUIRED
# - Password -> REQUIRED

# 4) assign realm directGrantFlow to new flow
docker compose exec -T keycloak $KCADM update realms/aviation -s "directGrantFlow=$NEW"

# 5) disable blocking Required Actions (safe for this test environment)
for A in VERIFY_PROFILE UPDATE_PROFILE UPDATE_PASSWORD CONFIGURE_TOTP; do
  docker compose exec -T keycloak $KCADM update "authentication/required-actions/$A" -r aviation -s enabled=false || true
done
```

### Validation (PASS/FAIL)

```bash
ISSUER_LOCAL="http://localhost:8080/realms/aviation"
CLIENT_ID="aviation-api"
PASS='Camo1234!@'

# CAMO
curl -sS -X POST "$ISSUER_LOCAL/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=$CLIENT_ID"   -d "username=camo_lot" -d "password=$PASS"   -o /tmp/token_camo_local.json

python3 - <<'PY'
import json, base64
o=json.load(open("/tmp/token_camo_local.json"))
t=o.get("access_token")
print("has_token:", bool(t))
if not t:
    print("FAIL:", o); raise SystemExit(1)
p=json.loads(base64.urlsafe_b64decode(t.split(".")[1] + "==="))
print("preferred_username:", p.get("preferred_username"))
print("tenant_id:", p.get("tenant_id"))
print("roles:", (p.get("realm_access") or {}).get("roles"))
PY

# MRO
curl -sS -X POST "$ISSUER_LOCAL/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=$CLIENT_ID"   -d "username=mro_lotams" -d "password=$PASS"   -o /tmp/token_mro_local.json

python3 - <<'PY'
import json, base64
o=json.load(open("/tmp/token_mro_local.json"))
t=o.get("access_token")
print("has_token:", bool(t))
if not t:
    print("FAIL:", o); raise SystemExit(1)
p=json.loads(base64.urlsafe_b64decode(t.split(".")[1] + "==="))
print("preferred_username:", p.get("preferred_username"))
print("tenant_id:", p.get("tenant_id"))
print("roles:", (p.get("realm_access") or {}).get("roles"))
PY
```

**PASS criteria**
- `has_token: True`
- `tenant_id` claim present and equals expected tenant UUID.

## Token retrieval troubleshooting

**Update 2026-01-12**

### Token (Keycloak) — common pitfalls

1) **Use correct clientId**  
In `infra/docker/keycloak/realm-aviation.json` the public client for direct grants is `aviation-api`.

2) **Passwords containing `!` in bash**  
In interactive bash, `!` triggers history expansion and breaks commands. Use single quotes around the password, or disable history expansion:

```bash
PASS='qwe123!@#'      # safe
# or: set +H
```

3) **Validate you really got a JWT**  
A valid access token has **two dots** (`header.payload.signature`):

```bash
echo "TOKEN_DOTS=$(echo "$TOKEN" | awk -F. '{print NF-1}')"   # expect: 2
```

### Minimal server-side token command (password grant)

```bash
KC="http://localhost:8080"
REALM="aviation"
CLIENT_ID="aviation-api"
USER="platformadmin"
PASS='__YOUR_PASSWORD__'

TOKEN=$(curl -sS   -d "grant_type=password"   -d "client_id=$CLIENT_ID"   -d "username=$USER"   -d "password=$PASS"   "$KC/realms/$REALM/protocol/openid-connect/token" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
```

### Tenant UUID lookup (server)

```bash
docker compose exec db psql -U aviation -d aviation -c "select id,name,slug from public.tenants order by name;"
```
