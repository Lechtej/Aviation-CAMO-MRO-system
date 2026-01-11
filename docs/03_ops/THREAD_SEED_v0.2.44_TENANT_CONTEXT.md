# WSAD DO NOWEGO WĄTKU — v0.2.44 — TENANT CONTEXT FINALIZATION (UI → API)

## TEMAT
v0.2.44 — Domknięcie tenant context dla UI po HTTPS:
login (Keycloak OIDC code+PKCE) → token → wybór tenanta → API calls:
- `GET /v1/aircraft`
- `GET /v1/maintenance-events`

## KONTRAKT PRACY
- Jeden cel wątku: UI działa po HTTPS i “read-only” działa po zalogowaniu **w tenant-scope**.
- Mikro-kroki: 1 komenda / 1 zmiana → wynik PASS/FAIL. Dopiero po PASS następny krok.
- Brak zgadywania: decyzje tylko na podstawie logów/konfigu/kodu/screenów.
- Nie wracamy do rzeczy z PASS.

## STAN STARTOWY (POTWIERDZONE)
- UI: https://app.forgemotionsystems.com
- API: https://api.forgemotionsystems.com
- Keycloak: https://auth.forgemotionsystems.com
- OIDC issuer: https://auth.forgemotionsystems.com/realms/aviation
- Login działa, token jest w `localStorage["aviationcamo_auth_v1"]`
- `/v1/roles` → 200 (token ważny)
- `/v1/tenants` → 200 (lista tenantów)
- `/v1/aircraft` → 403 (tenant context nie jest resolvowany dla endpointu)

## FAKT: REGUŁY TENANT CONTEXT (backend)
Z middleware:
1) `X-Tenant-Id` (UUID) **tylko dla** `PLATFORM_ADMIN`
2) claim JWT: `tenant_id`
3) debug: `X-Debug-Tenant-Id` gdy `DEBUG_TENANT_HEADER=true`

Dokument: `docs/02_api/TENANT_CONTEXT.md`

## CEL KOŃCOWY (DoD)
Wszystkie testy PASS:
1) UI: `GET /v1/aircraft` → 200 + JSON
2) API response zawiera:
   - `X-Tenant-Id`
   - `X-Tenant-Schema`
3) UI wysyła tenant context zgodnie z wybranym modelem:
   - Model A (prod): `tenant_id` claim w JWT **albo**
   - Model B (admin): `X-Tenant-Id` w request headers

## START — MIKRO-KROK 1 (TEST, ZERO ZMIAN)
Cel: potwierdzić aktywną ścieżkę tenant-context dla `platformadmin` poprzez ręczny request z tenant headerem.

W DevTools → Console (na `https://app.forgemotionsystems.com`) wykonaj:
- pobierz tenant id z `/v1/tenants`
- wywołaj `/v1/aircraft` z headerem `X-Tenant-Id: <TENANT_UUID>`

PASS = 200 + response headers `X-Tenant-*`

Wklej: status + pierwsze 200 znaków odpowiedzi + (jeśli widać) `X-Tenant-Source`.



---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-11 — Verified E2E commands (server-side)

### A) Enable debug tenant routing (temporary)
- In `docker-compose.yml` (service `api`):
  - `DEBUG_TENANT_HEADER: "true"`

Sanity:
```bash
docker compose up -d --force-recreate api
docker compose exec api bash -lc 'echo "DEBUG_TENANT_HEADER=$DEBUG_TENANT_HEADER"'
```
Expected: `DEBUG_TENANT_HEADER=true`

### B) Get token (server-side test)
```bash
ISS="https://auth.forgemotionsystems.com/realms/aviation"
TOK="$ISS/protocol/openid-connect/token"

curl -sS -X POST "$TOK"   -H "Content-Type: application/x-www-form-urlencoded"   --data-urlencode "grant_type=password"   --data-urlencode "client_id=aviation-api"   --data-urlencode "username=camo_user"   --data-urlencode "password=qwe123!@#"   | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
```

### C) Call API with explicit tenant
```bash
curl -sS -i   -H "Authorization: Bearer $TOKEN"   -H "X-Debug-Tenant-Id: <TENANT_UUID>"   https://api.forgemotionsystems.com/v1/aircraft | head
```

### D) After verification
- Set `DEBUG_TENANT_HEADER=false`.
- Move to **token-based tenant** (`tenant_id` claim) for production.

## ADDENDUM 2026-01-11 — What changed after the thread seed was written

### Keycloak: separate UI client (public)
- A dedicated Keycloak client for the browser UI is required.
- **Client:** `aviation-ui` (public client, standard flow, PKCE S256)
- Redirect URIs MUST include the exact deployed origin, e.g. `https://app.forgemotionsystems.com/*`.

### UI: tenant bootstrap for demo
- UI can use `X-Debug-Tenant-Id` header for E2E only when API has `DEBUG_TENANT_HEADER=true`.
- After `tenant_id` claim is present in the token, remove debug header usage from UI.

### Practical DoD for EPIC0B B1
- `GET /v1/aircraft` returns data for selected tenant.
- API response includes: `X-Tenant-Id`, `X-Tenant-Schema`, `X-Tenant-Source`.
- CORS preflight from `app.*` to `api.*` is HTTP 200.

## ADDENDUM 2026-01-11 — DoD / closure checklist (WĄTEK #6 EPIC0B B1)

### Definition of Done (pragmatyczne)

PASS jeśli:

1) `docker compose config` dla stacka jest poprawny (YAML valid).
2) API zwraca /docs HTTP 200 na `https://api.../docs`.
3) API call z tokenem + tenant context zwraca HTTP 200 (np. `/v1/aircraft`).
4) Response ma debug nagłówki: `x-tenant-id`, `x-tenant-schema`, `x-tenant-source`.
5) UI (https://app...) potrafi:
   - wykonać redirect do Keycloak,
   - wrócić na `https://app.../` po login (callback),
   - wykonać requesty do API na `https://api...` (CORS OK).

### Minimalny zestaw parametrów środowiskowych (API)

- `DEBUG_TENANT_HEADER=true` tylko na dev/demo.
- Na prod: `DEBUG_TENANT_HEADER=false` + wymuszenie `tenant_id` claim.

### Najczęstsze FAIL

- `Invalid parameter: redirect_uri` → brak klienta `aviation-ui` albo brak `redirectUris` dla `https://app.../*`.
- `Failed to fetch` w UI → CORS (Origin), błędny base URL, blokada mixed-content lub błąd TLS.
- `401/403` po login → brak roli w tokenie lub brak tenant context.

## ADDENDUM 2026-01-11 - E2E: UI + tenant debug header

### Zaleznosci / warunki wstepne

* API: `DEBUG_TENANT_HEADER=true` (tylko dev/E2E)
* UI: uzywa klienta Keycloak `aviation-ui` (standard flow + PKCE)
* UI: do requestow API doklada `X-Debug-Tenant-Id: <TENANT_UUID>` (tymczasowo)

### Szybki test po zalogowaniu

1) Zaloguj sie w UI.
2) Otworz `#/camo/aircraft`.
3) W DevTools -> Network sprawdz, czy request ma:
   * `Authorization: Bearer ...`
   * `X-Debug-Tenant-Id: ...`
4) Oczekiwane: HTTP 200 + naglowki `x-tenant-*`.

### Ryzyko i DoD

* `DEBUG_TENANT_HEADER` **MUST** byc `false` w prod.
* DoD EPIC0B B1: routing dziala na podstawie token claim `tenant_id` lub `X-Tenant-Id` (PLATFORM_ADMIN).

## ADDENDUM 2026-01-11 - UI smoke test (HTTPS + OIDC + tenant header)

Poniżej minimalny smoketest łączący wszystkie elementy z wątku #6 (B1) oraz HTTPS/OIDC.

### 1) API działa (bez auth)
* `GET https://api.forgemotionsystems.com/docs` -> **200**

### 2) Token (CLI) i tenant routing (debug)
* uzyskaj token z Keycloak (Direct Access Grants) dla `aviation-api` (CLI)
* wywołaj API z tenantem:
  * `X-Debug-Tenant-Id: <TENANT_UUID>` (tylko gdy `DEBUG_TENANT_HEADER=true`)
  * spodziewane response headers: `x-tenant-id`, `x-tenant-schema`, `x-tenant-source=header(debug)`

### 3) UI login
* UI musi używać klienta **aviation-ui** (PKCE): inaczej dostaniesz `Invalid parameter: redirect_uri`.
* po loginie wracasz na `https://app.forgemotionsystems.com/` z parametrami `code` + `state`.

### 4) UI -> API
Po udanym token exchange UI wysyła:
* `Authorization: Bearer <access_token>`
* tenant context:
  * w DEV/DEMO: `X-Debug-Tenant-Id: <TENANT_UUID>`
  * w PROD: `tenant_id` w tokenie (claim) lub `X-Tenant-Id` tylko dla PLATFORM_ADMIN

PASS/FAIL kryteria:
* PASS: UI pokazuje `API: OK`, a listy `/v1/aircraft` i `/v1/maintenance-events` zwracają dane (200)
* FAIL: `Failed to fetch` -> sprawdź CORS, baseUrl, token, tenant source w response headers
