#24 — DMS Stabilization + DMS Types Seed + Auth/Issuer consistency (API+Scripts)

## Cel (jednoznaczny)
- Domknąć DMS w backendzie jako stabilny moduł (MVP): `/v1/dms/types` + `/v1/dms/documents` (+ lifecycle jeśli istnieje).
- Ujednolicić dev-ops: token zawsze pobierany z tego samego `OIDC_ISSUER`, którego używa API (zero `Invalid issuer`, zero `expired token`).
- Doprowadzić do PASS smoke testów dla DMS i spiąć addytywnie z dokumentacją.

## Stan wejściowy (FAKTY / PASS)
- `/v1/dms/types` wcześniej: `500 ResponseValidationError` dla `EASA_FORM_1` (domain literal).
- Backend dostosowany: `DmsDomain` dopuszcza `EASA` → `/v1/dms/types` zwraca `200 OK` i rekordy z `domain:"EASA"`.
- `OIDC_ISSUER=https://auth.forgemotionsystems.com/realms/aviation`
- `OIDC_JWKS_URL=http://keycloak:8080/realms/aviation/protocol/openid-connect/certs`

## Decyzja projektowa
**Decyzja A = utrzymujemy `EASA` w enum `DmsDomain`.**
Konsekwencja: API/Schema/OpenAPI muszą mieć spójne enum.

## Krok 1 — weryfikacja OIDC w API (source of truth)
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

docker exec -i docker-api-1 sh -lc 'printf "OIDC_ISSUER=%s\nOIDC_JWKS_URL=%s\n" "$OIDC_ISSUER" "$OIDC_JWKS_URL"'
```
PASS jeśli `OIDC_ISSUER` i `OIDC_JWKS_URL` jak wyżej.

## Krok 2 — token + smoke DMS (bez UI)
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system
chmod +x scripts/dev/get_token_dev.sh scripts/dev/smoke_dms.sh

scripts/dev/smoke_dms.sh 234b8a8c-549a-4922-8b82-334c62a2aa1c | sed -n '1,220p'
```
PASS jeśli:
- `/v1/dms/types` → HTTP 200 + JSON lista
- `/v1/dms/documents` → HTTP 200 (może być `[]`)

## Diagnostyka (tylko gdy FAIL)
```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

docker compose ps
docker compose logs --tail=250 api
```

## Notatka operacyjna (anti-regression)
- Tokeny do testów **zawsze** pobieramy z `OIDC_ISSUER` wyciągniętego z kontenera API.
- Nie mieszamy `localhost/http` z `https://auth...` w obrębie jednego JWT.
