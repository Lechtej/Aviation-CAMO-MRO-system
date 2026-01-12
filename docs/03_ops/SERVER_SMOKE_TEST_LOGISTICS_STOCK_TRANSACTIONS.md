# Server smoke test — Logistics /stock-transactions

**Added 2026-01-12 (additive doc).**

## Preconditions

- stack up: `infra/docker/docker-compose.yml`
- valid Keycloak user (example: `platformadmin`)
- known `TENANT_ID` (UUID) and `STOCK_ID` (UUID)

## 1) Obtain token

```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker

KC="http://localhost:8080"
REALM="aviation"
CLIENT_ID="aviation-api"
USER="platformadmin"
PASS='__YOUR_PASSWORD__'   # use single quotes if contains !

TOKEN=$(curl -sS   -d "grant_type=password"   -d "client_id=$CLIENT_ID"   -d "username=$USER"   -d "password=$PASS"   "$KC/realms/$REALM/protocol/openid-connect/token" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

echo "TOKEN_DOTS=$(echo "$TOKEN" | awk -F. '{print NF-1}')"   # expect 2
```

## 2) Get tenant UUID

```bash
docker compose exec db psql -U aviation -d aviation -c "select id,name,slug from public.tenants order by name;"
```

Pick `id` and set:

```bash
TENANT_ID="__UUID_FROM_DB__"
```

## 3) POST stock transaction (RECEIPT)

```bash
STOCK_ID="__STOCK_ITEM_UUID__"

curl -sS -i -X POST   -H "Authorization: Bearer $TOKEN"   -H "X-Tenant-Id: $TENANT_ID"   -H "Content-Type: application/json"   "http://127.0.0.1:8000/v1/logistics/stock-transactions"   --data "{\"type\":\"RECEIPT\",\"stock_item_id\":\"$STOCK_ID\",\"qty\":5}"
```

Expected:
- `201` and JSON with `transaction_id`, `stock_item_id`, `qty_on_hand`.

## Known errors

- `401 Invalid token: Signature has expired` → token TTL exceeded; request a new token.
- `500 ... badly formed hexadecimal UUID string` → invalid `X-Tenant-Id` (not UUID).
- `404 Stock item not found` → wrong `STOCK_ID` or wrong tenant.
