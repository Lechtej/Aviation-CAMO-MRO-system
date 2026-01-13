# Server Smoke Test – Keycloak / OIDC (client_credentials)


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

## Scope
Server-side smoke test for AviationCAMO-MRO-system:
- Keycloak OIDC
- client_credentials
- PLATFORM_ADMIN
- Tenant bootstrap
- Logistics & Inventory happy-path

---

## Preconditions
- Docker + docker-compose
- keycloak / api / postgres containers running

---

## Token
Use client_credentials.
Regenerate often (short TTL).

---

## Tenant
Create tenant via /v1/tenants.
All tenant endpoints require X-Tenant-Id header.

---

## Logistics bootstrap
POST /v1/logistics/_admin/bootstrap

---

## Happy-path
- inventory part
- warehouse
- location
- stock-item

---

## Known issue
POST /v1/logistics/movements → 404 Not Found


## STATUS FREEZE (2026-01-10) — UI over HTTPS (OIDC code+PKCE) + API calls (read-only)

### Endpoints (prod)
- UI: https://app.forgemotionsystems.com
- API: https://api.forgemotionsystems.com
- Keycloak: https://auth.forgemotionsystems.com
- OIDC issuer: https://auth.forgemotionsystems.com/realms/aviation

### UI auth flow (SPA)
- Protocol: Authorization Code + PKCE (S256)
- Token storage: `localStorage["aviationcamo_auth_v1"]`
- Expected redirect_uri: `https://app.forgemotionsystems.com/`

### Keycloak client settings (minimum)
Client: `aviation-api` (realm: `aviation`)
- Valid Redirect URIs:
  - `https://app.forgemotionsystems.com/`
  - `https://app.forgemotionsystems.com/*`
- Web Origins:
  - `https://app.forgemotionsystems.com`

### Production CORS requirement (browser)
API must allow origin:
- `https://app.forgemotionsystems.com`

Note:
- verify with preflight (OPTIONS) against `/v1/aircraft` using that origin.

### Tenant context requirement (current)
Tenant-scoped endpoints (e.g. `/v1/aircraft`) require tenant context to be resolved.
Resolution rules are documented in:
- `docs/02_api/TENANT_CONTEXT.md`

### Smoke-test checklist (PASS/FAIL)
1) UI secure context:
   - `window.isSecureContext === true` (browser console)
2) PKCE availability:
   - `crypto.subtle.digest` exists
3) Login redirect:
   - host `auth.forgemotionsystems.com`
   - `code_challenge_method=S256`
4) After login:
   - `localStorage["aviationcamo_auth_v1"].access_token` exists
5) API connectivity:
   - `GET /docs` → 200 (UI shows API OK)
6) Auth:
   - `GET /v1/roles` with Bearer → 200
7) Tenant:
   - `GET /v1/aircraft`:
     - without tenant context → may be 403
     - with tenant context (claim or `X-Tenant-Id`) → 200



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---

## Update 2026-01-11 – Smoke test OIDC (password grant) + RBAC matrix na DEV

Ten rozdział rozszerza smoke test o:
- token dla użytkowników (Direct Access Grants / `grant_type=password`) – szybka walidacja roli i `tenant_id`,
- pobranie `/openapi.json` oraz automatyczne wypisanie endpointów GET,
- macierz RBAC (mini-regresja) na kilku rolach.

### 1) Pobranie OpenAPI z serwera
```bash
API="https://api.forgemotionsystems.com"
curl -sS -D /tmp/openapi.h -o /tmp/openapi.json "$API/openapi.json"
sed -n '1,20p' /tmp/openapi.h
ls -lh /tmp/openapi.json
head -c 200 /tmp/openapi.json; echo
```

### 2) Lista ścieżek GET (z OpenAPI)
```bash
python3 - <<'PY'
import json
o=json.load(open("/tmp/openapi.json","r",encoding="utf-8"))
paths=o.get("paths",{})
get_paths=[]
for p,methods in paths.items():
  if "get" in (k.lower() for k in methods.keys()):
    get_paths.append(p)
for p in sorted(get_paths):
  print(p)
PY
```

### 3) Token użytkownika (password grant) + dekodowanie claimów
```bash
ISSUER="https://auth.forgemotionsystems.com/realms/aviation"
CLIENT_ID="aviation-api"
USER="mro_lotams"
PASS='Camo1234!@'

curl -sS -o /tmp/token.json -X POST "$ISSUER/protocol/openid-connect/token"   -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password" -d "client_id=$CLIENT_ID" -d "username=$USER" -d "password=$PASS"

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
```

### 4) Mini-regresja RBAC (na podstawie listy krytycznych endpointów)
Wersja „na szybko” – sprawdza, czy:
- CAMO ma dostęp do `/v1/aircraft` oraz może tworzyć,
- MRO/STORES nie mają dostępu do CAMO-only,
- `_admin` wymaga `PLATFORM_ADMIN`,
- część endpointów logistyki jest tymczasowo „szeroka” (do doprecyzowania w backlogu).

```bash
set -euo pipefail

ISSUER="https://auth.forgemotionsystems.com/realms/aviation"
API="https://api.forgemotionsystems.com"
CLIENT_ID="aviation-api"
PASS='Camo1234!@'

USERS=(camo_lot mro_lotams mro_lst stores_lotams)

get_token () {
  local U="$1"
  curl -sS -X POST "$ISSUER/protocol/openid-connect/token"     -H "Content-Type: application/x-www-form-urlencoded"     -d "grant_type=password" -d "client_id=$CLIENT_ID" -d "username=$U" -d "password=$PASS"   | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))'
}

hit () {
  local token="$1"
  local method="$2"
  local path="$3"
  local data="${4:-}"

  if [[ "$method" == "GET" ]]; then
    curl -sS -o /tmp/r.json -w "%{http_code}"       -H "Authorization: Bearer $token"       "$API$path"
  else
    curl -sS -o /tmp/r.json -w "%{http_code}"       -H "Authorization: Bearer $token"       -H "Content-Type: application/json"       -X "$method" "$API$path" --data-binary "$data"
  fi
}

# CAMO setup: list aircraft -> pick id
echo "== CAMO setup =="
TOK_CAMO=$(get_token camo_lot)
code=$(hit "$TOK_CAMO" GET /v1/aircraft)
echo "camo_lot GET /v1/aircraft -> $code"
AIRCRAFT_ID=$(python3 - <<'PY'
import json
a=json.load(open("/tmp/r.json"))
print((a[0]["id"] if a else ""))
PY
)
echo "AIRCRAFT_ID=$AIRCRAFT_ID"

echo
echo "== RBAC matrix =="

for U in "${USERS[@]}"; do
  T=$(get_token "$U")
  echo
  echo "===== $U (token bytes: ${#T}) ====="
  test ${#T} -gt 100 || { echo "FAIL: empty token for $U"; exit 1; }

  for SPEC in     "GET  /v1/aircraft"     "POST /v1/aircraft {'registration':'SP-TEST1'}"     "GET  /v1/maintenance-events?aircraft_id=$AIRCRAFT_ID"     "GET  /v1/logistics/warehouses"     "GET  /v1/logistics/locations"     "GET  /v1/logistics/stock-items"     "GET  /v1/logistics/uom"     "GET  /v1/logistics/parts"     "GET  /v1/inventory/parts"     "GET  /v1/roles"     "GET  /v1/tenants"
  do
    method=$(echo "$SPEC" | awk '{print $1}')
    path=$(echo "$SPEC" | awk '{print $2}')
    data=$(echo "$SPEC" | sed -n 's/^[A-Z]* [^ ]* //p' | sed "s/'/"/g")

    code=$(hit "$T" "$method" "$path" "$data")
    detail=$(python3 -c 'import json; o=json.load(open("/tmp/r.json")); print(o.get("detail","") if isinstance(o,dict) else "")' 2>/dev/null || true)

    printf "%-8s %-40s -> %s%s
" "$method" "$path" "$code" "${detail:+ | $detail}"
  done
done
```

## Troubleshooting: `invalid_grant` / `Account is not fully set up` (Password Grant)

If `/protocol/openid-connect/token` returns:
- `invalid_grant` + `Account is not fully set up`

Then the realm Direct Grant flow is blocking password grant (commonly OTP / profile checks).
Apply the fix procedure from:
- `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md` → **Fix: invalid_grant / Account is not fully set up**

---

## Update 2026-01-13 — tokeny w PROD i `unauthorized_client`

### Problem: `unauthorized_client` przy token endpoint (password grant)
Jeżeli przy wywołaniu:
- `POST /realms/<realm>/protocol/openid-connect/token` z `grant_type=password`
dostajesz:
- `{"error":"unauthorized_client","error_description":"Client not allowed for direct access grants"}`

to znaczy, że **klient nie ma włączonego Direct Access Grants**. To jest poprawne i pożądane w produkcji dla klienta UI.

### Najprostsza ścieżka w PROD: token z UI (Authorization Code + PKCE)
1) Zaloguj się w UI: `https://app.forgemotionsystems.com`
2) Otwórz DevTools → Application/Storage → `localStorage` (lub Network → response z tokenami)
3) Skopiuj `access_token` (ciąg zaczynający się od `eyJ...` z **2 kropkami**).

#### Szybki test w bash bez wklejania do komend (bez echa)
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

umask 077
read -s -p "PASTE access_token (JWT, 1 linia): " TOKEN; echo

# walidacja JWT shape + TTL (bez weryfikacji podpisu)
TOKEN="$TOKEN" python3 - <<'PY'
import os, time, json, base64
t=os.environ["TOKEN"].strip()
print("len:", len(t), "dots:", t.count("."))
if t.count(".") != 2:
    raise SystemExit("FAIL: to nie jest JWT (muszą być 2 kropki)")
h,p,_=t.split(".",2)
def d(s): s+="="*(-len(s)%4); return base64.urlsafe_b64decode(s.encode())
pl=json.loads(d(p))
now=int(time.time())
exp=int(pl.get("exp",0))
print("ttl_sec:", exp-now)
print("iss:", pl.get("iss"))
print("azp:", pl.get("azp"))
print("roles:", (pl.get("realm_access") or {}).get("roles"))
PY

# 1) Keycloak /userinfo (powinno być 200 jeśli token ważny)
curl -sS -D- -o /dev/null   -H "Authorization: Bearer $TOKEN"   https://auth.forgemotionsystems.com/realms/aviation/protocol/openid-connect/userinfo | sed -n '1,40p'

# 2) API call (powinno być 200, jeśli tenant podany i token ważny)
curl -sS -D- -o /dev/null   -H "Authorization: Bearer $TOKEN"   -H "X-Tenant-Id: <TENANT_UUID>"   https://api.forgemotionsystems.com/v1/aircraft | sed -n '1,40p'

unset TOKEN
```

**Interpretacja wyników**
- `ttl_sec < 0` → token jest przeterminowany (to był case: `ttl_sec: -300`) → pobierz nowy z UI.
- `/userinfo` → `401 invalid_token` → token nieważny (najczęściej expiry) lub issuer/realm nie pasuje.
- API `401` przy poprawnym `/userinfo 200` → problem po stronie API weryfikacji JWT (issuer/audience/JWKS) albo brak tenant context.

### Uwaga: token musi być "jedną linią"
Jeżeli w terminalu wychodzi `dots: 0/1`, to wkleiłeś:
- placeholder typu `PASTE_ACCESS_TOKEN_HERE`, albo
- token z cudzysłowami/enterami, albo
- fragment JSON zamiast samego JWT.

Kopiuj **tylko wartość** `access_token`, bez `"access_token":` i bez cudzysłowów.

### Alternatywa DEV: włączyć Direct Access Grants tylko na czas testu
Jeżeli potrzebujesz password grant w DEV:
- Keycloak → Client → Settings → **Direct Access Grants Enabled: ON**
- po teście wróć na OFF (ryzyko bezpieczeństwa).
