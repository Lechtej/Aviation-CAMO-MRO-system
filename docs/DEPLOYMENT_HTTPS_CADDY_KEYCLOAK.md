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

