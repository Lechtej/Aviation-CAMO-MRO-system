# Deployment HTTPS (Caddy + Keycloak)

## Cel
Zapewnienie pełnego HTTPS (TLS terminated at Caddy) dla:
- app.forgemotionsystems.com (UI)
- api.forgemotionsystems.com (FastAPI)
- auth.forgemotionsystems.com (Keycloak)

## Stan końcowy (DoD)
- Wszystkie subdomeny dostępne wyłącznie po HTTPS
- Keycloak generuje poprawne URL-e bez :8080
- OIDC issuer i JWKS zgodne z publicznym URL
- Password grant działa w realm `aviation`

---

## Architektura
- **Caddy**: terminacja TLS (Let's Encrypt), reverse proxy
- **Keycloak**: HTTP na 8080, proxy-aware
- **API**: weryfikacja JWT po JWKS z Keycloak

```
Internet -> HTTPS -> Caddy :443 -> HTTP -> Containers
```

---

## Caddyfile (FINAL)
```caddy
{
    email admin@forgemotionsystems.com
}

app.forgemotionsystems.com {
    reverse_proxy 127.0.0.1:3000
}

api.forgemotionsystems.com {
    reverse_proxy 127.0.0.1:8000
}

auth.forgemotionsystems.com {
    reverse_proxy 127.0.0.1:8080
}
```

---

## Docker Compose – Keycloak (FINAL)
```yaml
keycloak:
  image: quay.io/keycloak/keycloak:25.0
  command: start-dev --import-realm
  volumes:
    - ./keycloak:/opt/keycloak/data/import
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin
    KC_BOOTSTRAP_ADMIN_USERNAME: admin
    KC_BOOTSTRAP_ADMIN_PASSWORD: admin

    KC_PROXY_HEADERS: xforwarded
    KC_HOSTNAME: https://auth.forgemotionsystems.com
    KC_HOSTNAME_ADMIN: https://auth.forgemotionsystems.com
    KC_HOSTNAME_STRICT: "true"
    KC_HTTP_ENABLED: "true"
  ports:
    - "8080:8080"
```

---

## OIDC – wartości produkcyjne
- Issuer: `https://auth.forgemotionsystems.com/realms/aviation`
- JWKS: `https://auth.forgemotionsystems.com/realms/aviation/protocol/openid-connect/certs`

---

## Testy walidacyjne
1. Certyfikaty:
```
curl -I https://auth.forgemotionsystems.com
```
2. OIDC discovery:
```
curl https://auth.forgemotionsystems.com/realms/aviation/.well-known/openid-configuration
```
3. Password grant (admin-cli):
```
POST /realms/aviation/protocol/openid-connect/token
```
HTTP 200 = OK

---

## Known issues / TODO
- Brak endpointów `/health`, `/readyz` w API (FastAPI)  
  **TODO**: dodać standardowe health-check endpoints (Kubernetes / monitoring)
- `admin-cli` wymaga jawnego `directAccessGrantsEnabled=true` po imporcie realm
- `start-dev` – przed produkcją przejść na `start --optimized`


## 2026-01-10 — UI HTTPS (SPA) operational notes

### UI config (static `app.js`)
Production UI uses hardcoded defaults inside `apps/web/app.js`:
- `DEFAULT_BASE_URL = "https://api.forgemotionsystems.com"`
- `KC.baseUrl = "https://auth.forgemotionsystems.com"`
- `KC.realm = "aviation"`
- `KC.clientId = "aviation-api"`

If UI serves stale `app.js` (still points to localhost), validate:
- `curl -s https://app.forgemotionsystems.com/app.js | grep -E "DEFAULT_BASE_URL|KC\.baseUrl"`

### Container reality check (where code actually runs)
Some containers ship code into `/app/...` at image build time.
If you edit repo files on host and changes are not visible in runtime:
- verify the live file inside container
- then rebuild the image OR apply a temporary hotfix via `docker cp` (unblock only)

Recommended long-term:
- rebuild `docker-api` and `docker-web` images from the updated repo to make changes persistent across restarts/redeploys.



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-11 — UI client for PKCE (fix for `Invalid parameter: redirect_uri`)

### Problem
UI was using Keycloak client `aviation-api` (confidential / API client). Keycloak rejected the browser redirect URI.

### Decision
Create a **separate public client** for the browser UI:
- `clientId: aviation-ui`
- `publicClient: true`
- `standardFlowEnabled: true` (Authorization Code)
- `PKCE S256`
- `redirectUris: ["https://app.forgemotionsystems.com/*"]`
- `webOrigins: ["https://app.forgemotionsystems.com"]`

### kcadm (repeatable)
```bash
# login
kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password 'admin123!'

# create UI client (public)
kcadm.sh create clients -r aviation   -s clientId=aviation-ui   -s enabled=true   -s publicClient=true   -s standardFlowEnabled=true   -s implicitFlowEnabled=false   -s directAccessGrantsEnabled=false   -s serviceAccountsEnabled=false   -s 'redirectUris=["https://app.forgemotionsystems.com/*"]'   -s 'webOrigins=["https://app.forgemotionsystems.com"]'

# sanity
kcadm.sh get clients -r aviation -q clientId=aviation-ui --fields clientId,publicClient,redirectUris,webOrigins
```

### UI config
In UI (static `app.js`) set:
- `KC.clientId = "aviation-ui"`

(keep API client separate; never use password grants from the browser).

## ADDENDUM 2026-01-11 — UI client (aviation-ui) and redirect_uri fix

### Problem
- Browser OIDC login failed with: **"Invalid parameter: redirect_uri"**.

### Root cause
- UI was using clientId `aviation-api` (confidential/service style), but the browser requires a **public** client with correct `redirectUris` and `webOrigins`.

### Fix (Keycloak)
Create **public** client `aviation-ui`:

```bash
# login kcadm (master)
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password 'admin123!'

# create client
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create clients -r aviation \
  -s clientId=aviation-ui \
  -s enabled=true \
  -s publicClient=true \
  -s standardFlowEnabled=true \
  -s implicitFlowEnabled=false \
  -s directAccessGrantsEnabled=false \
  -s serviceAccountsEnabled=false \
  -s 'redirectUris=["https://app.forgemotionsystems.com/*"]' \
  -s 'webOrigins=["https://app.forgemotionsystems.com"]' \
  -s 'attributes."pkce.code.challenge.method"="S256"'

# sanity check
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r aviation -q clientId=aviation-ui \
  --fields clientId,publicClient,redirectUris,webOrigins,attributes
```

### Fix (UI)
- UI must use **clientId = `aviation-ui`** in OIDC requests.
- UI must use `https://app.forgemotionsystems.com/` as `redirect_uri` (same origin as served UI).

### Notes
- Keep API client `aviation-api` for service-to-service / password grant testing.
- Do not enable password grant on the browser client.

## ADDENDUM 2026-01-11 — UI client + redirect URI (fix „Invalid parameter: redirect_uri”)

Problem: UI używa OIDC Authorization Code + PKCE i wysyła `redirect_uri=https://app.forgemotionsystems.com/`.
Keycloak odrzuca logowanie jeśli **client** nie ma dopuszczonego tego redirect URI.

### Decyzja

- **Browser UI** używa osobnego klienta Keycloak: `aviation-ui` (public client).
- **API** zostaje przy `aviation-api` (client credentials / password grant / introspection wg potrzeb).

### Minimalna konfiguracja Keycloak (kcadm)

> Uwaga: uruchamiaj wewnątrz hosta z docker-compose (server: `http://localhost:8080`).

1) Login do kcadm:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials   --server http://localhost:8080   --realm master   --user admin   --password 'admin123!'
```

2) Utwórz klienta UI:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create clients -r aviation   -s clientId=aviation-ui   -s enabled=true   -s publicClient=true   -s standardFlowEnabled=true   -s implicitFlowEnabled=false   -s directAccessGrantsEnabled=false   -s serviceAccountsEnabled=false   -s 'redirectUris=["https://app.forgemotionsystems.com/*"]'   -s 'webOrigins=["https://app.forgemotionsystems.com"]'
```

3) Sanity check:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r aviation   -q clientId=aviation-ui --fields clientId,publicClient,redirectUris,webOrigins
```

### Minimalna zmiana w UI (app.js)

W pliku UI ustaw `KC.clientId = "aviation-ui"`.

> Jeśli UI jest serwowane jako statyczne pliki w kontenerze `web` (python `http.server`), modyfikacja dotyczy `/app/app.js`.

### Ryzyko

Jeśli UI i API współdzielą ten sam clientId, rośnie ryzyko błędów konfiguracyjnych (redirect URI / public vs confidential) i mieszania flow.
Rozdzielenie klientów minimalizuje rework i upraszcza audyt.

## ADDENDUM 2026-01-11 - UI (PKCE) client + redirect_uri

### Problem: `Invalid parameter: redirect_uri`

Objaw: po kliknieciu **Login** Keycloak pokazuje blad `Invalid parameter: redirect_uri`.

Przyczyna: UI uzywalo clienta `aviation-api` (klient backendowy / confidential lub bez poprawnych redirect URIs).

### Rozwiazanie docelowe

1) W Keycloak utworz osobny klient dla UI (public, standard flow, PKCE):

* `clientId`: **aviation-ui**
* `publicClient`: **true**
* `standardFlowEnabled`: **true**
* `redirectUris`: `https://app.forgemotionsystems.com/*`
* `webOrigins`: `https://app.forgemotionsystems.com`

2) W UI ustaw `KC.clientId = "aviation-ui"`.

### kcadm.sh (przyklad)

```bash
# login do master
kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password 'admin123!'

# create client
kcadm.sh create clients -r aviation   -s clientId=aviation-ui   -s enabled=true   -s publicClient=true   -s standardFlowEnabled=true   -s directAccessGrantsEnabled=false   -s 'redirectUris=["https://app.forgemotionsystems.com/*"]'   -s 'webOrigins=["https://app.forgemotionsystems.com"]'
```

### Uwagi do MVP

W obecnym MVP UI moze dodawac header `X-Debug-Tenant-Id` (tylko przy `DEBUG_TENANT_HEADER=true`).
W produkcji docelowo przechodzimy na claim `tenant_id`.

## ADDENDUM 2026-01-11 - UI PKCE client (aviation-ui) + redirect_uri

### Problem
UI używa OIDC Authorization Code + PKCE. Próba logowania na kliencie **aviation-api** kończy się błędem **Invalid parameter: redirect_uri**, bo klient API nie ma dopuszczonych redirectUris dla domeny UI.

### Decyzja
* Dla UI utrzymujemy osobnego klienta Keycloak: **aviation-ui** (public client, standard flow, PKCE S256).
* Klient **aviation-api** pozostaje po stronie API (Direct Access Grants / password w testach CLI), ale **nie** jest używany w przeglądarce.

### Minimalny config klienta `aviation-ui`
W realm `aviation`:
* `publicClient=true`
* `standardFlowEnabled=true`
* `directAccessGrantsEnabled=false`
* `redirectUris=["https://app.forgemotionsystems.com/*"]`
* `webOrigins=["https://app.forgemotionsystems.com"]`

### kcadm.sh (idempotentnie - kontrola po wykonaniu)
Komendy (podane jako referencja operacyjna):
1) `kcadm.sh config credentials ...` (realm `master`)
2) `kcadm.sh create clients -r aviation ... clientId=aviation-ui ... redirectUris/webOrigins ...`
3) `kcadm.sh get clients -r aviation -q clientId=aviation-ui --fields clientId,publicClient,redirectUris,webOrigins`

### Zmiana w UI (app.js)
W stałych Keycloak w `app.js`:
* `clientId: "aviation-ui"` (zamiast `aviation-api`).

Ryzyko/uwagi:
* Jeżeli webOrigins/redirectUris są zbyt wąskie - logowanie będzie failować na etapie /auth.
* Jeżeli są zbyt szerokie - rośnie powierzchnia ataku (zostawiamy tylko domenę UI + wildcard path).
