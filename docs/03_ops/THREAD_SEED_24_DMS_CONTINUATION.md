# #24 — DMS stabilizacja + weryfikacja (BE + kontrakt)

## Kontekst
Wątek dotyczy **DMS** (Document Management System) w Aviation-CAMO-MRO-system.
UI regresje (lista aircraft/maintenance) są poza zakresem tego wątku.

## Stan wejściowy (PASS)
- API startuje poprawnie.
- `/v1/dms/types` działa po rebuild API.
- Zdiagnozowany i usunięty błąd 500 (`ResponseValidationError`) przez dopasowanie `DmsDomain` do danych seed.

## Root cause (history)
- Seed zawiera `EASA_FORM_1` z `domain=EASA`.
- `apps/api/src/modules/dms/schemas.py` miało `DmsDomain = Literal["CAMO","MRO","STORES"]`.
- FastAPI walidował response → 500.

## Fix (DONE)
- `DmsDomain` rozszerzone o `EASA`.
- Wymagany rebuild kontenera API:
  ```bash
  cd infra/docker
  docker compose up -d --build --force-recreate api
  ```

## Smoke / komendy referencyjne (DEV)
- Token z właściwego issuer (bez `-t` w docker exec):
  ```bash
  OIDC_ISSUER="$(docker exec -i docker-api-1 sh -lc 'printf "%s" "$OIDC_ISSUER"')"
  TOKEN="$(curl -sS -X POST "${OIDC_ISSUER}/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "client_id=aviation-api" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "username=platformadmin" \
    --data-urlencode "password=qwe1234@#" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')"
  ```
- Smoke DMS (repo):
  ```bash
  ./scripts/dev/smoke_dms.sh <TENANT_UUID>
  ```

## TODO w #24
1) **Kontrakt OpenAPI**: upewnić się, że statyczny `docs/02_api/openapi.yaml` zawiera:
   - enum `DmsDomain` z `EASA`
   - endpointy DMS (types/documents/lifecycle)
2) **Seed/data**: potwierdzić minimalny zestaw typów dokumentów dla LOT (PLL LOT).
3) **RBAC**: potwierdzić, które role/permissions są wymagane dla DMS (list types, create doc, lifecycle actions).

## Definition of Done
- `/v1/dms/types` i `/v1/dms/documents` działają na tenant `t_lot` (platformadmin).
- Runtime OpenAPI == statyczny `openapi.yaml` dla DMS.
- Dokumentacja DMS uzupełniona (append-only).
