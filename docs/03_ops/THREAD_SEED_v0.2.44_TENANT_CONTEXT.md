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

