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


## Update 2026-01-12 – Idempotency & UUID casting
- Confirmed correct runtime path: `/app/modules/logistics/router.py`.
- Fixed SQLAlchemy text() queries to use `CAST(:param AS uuid)` instead of `:param::uuid`.
- Smoke test PASS:
  - First ISSUE → HTTP 201, qty_on_hand decremented.
  - Repeated ISSUE with same Idempotency-Key → HTTP 409, no stock change.

---

## 2026-01-12 — Investigation notes (ledger mismatch) + safe psql workflow

### Symptom

- `stock_items.qty_on_hand` (snapshot) != suma z `stock_transactions` (ledger) dla `stock_item_id`.
- Przykład: snapshot 8.000 vs ledger -2.000 (3×ISSUE, 1×RETURN, bez RECEIPT).

### Root cause (MVP)

Snapshot (`stock_items`) został utworzony/ustawiony bez odpowiadającej mu transakcji bazowej w ledgerze (`stock_transactions`).
W modelu docelowym ledger powinien być źródłem prawdy, a snapshot powinien być pochodną.

### Mitigation applied (A — szybka naprawa danych)

Dodano brakującą transakcję `RECEIPT` (idempotentnie), tak aby:

- ledger wyliczał się do stanu snapshot
- zachować append-only semantics (`stock_transactions` ma triggery `no_update/no_delete`)

Minimalny zestaw pól NOT NULL w `public.stock_transactions` wymagany przy INSERT:

- `tenant_id` (uuid)
- `warehouse_id` (uuid)
- `part_id` (uuid)
- `transaction_type` (RECEIPT/ISSUE/RETURN)
- `qty` (>0)
- `uom` (np. 'EA')
- `idempotency_key` (unikalne)
- `created_by_user_id` (np. 'system')
- `created_by_username` (opcjonalnie)

### Safe psql workflow ("za rączkę")

Poniżej zestaw mikro-kroków, które są bezpieczne (read-only) oraz dwa wzorce „test update w transakcji”.

#### KROK 1 — Wejście do psql (server)

```bash
cd /opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker || exit 1
docker compose exec db psql -U aviation -d aviation
```

**PASS:** widzisz prompt `aviation=#`.

#### KROK 2 — Ustawienia interaktywne (żeby nie zawieszać terminala)

```sql
\pset pager off
\set ON_ERROR_STOP on
```

**PASS:** psql odpowiada `Pager usage is off.`

#### KROK 3 — Ustawienie schematu tenant (tylko gdy potrzebujesz tabel tenantowych)

```sql
SET search_path TO t_lot, public;
SHOW search_path;
```

**PASS:** `t_lot, public`.

#### KROK 4 — Identyfikacja kluczy dla INSERT (tenant/warehouse/part)

```sql
-- stock_item -> part_id, location_id
SELECT id, part_id, location_id, serial_number
FROM public.stock_items
WHERE id = '<STOCK_ITEM_ID>'::uuid;

-- location -> warehouse_id
SELECT id AS location_id, warehouse_id
FROM public.locations
WHERE id = '<LOCATION_ID>'::uuid;

-- tenant LOT (t_lot)
SELECT id AS tenant_id, code, schema_name
FROM public.tenants
WHERE code='lot' OR schema_name='t_lot';
```

**PASS:** masz 3 wartości UUID: `tenant_id`, `warehouse_id`, `part_id`.

#### KROK 5 — Reconciliation check (snapshot vs ledger)

```sql
SELECT
  si.id,
  si.qty_on_hand AS snapshot_qty,
  COALESCE(SUM(CASE
    WHEN st.transaction_type='RECEIPT' THEN st.qty
    WHEN st.transaction_type='ISSUE'   THEN -st.qty
    WHEN st.transaction_type='RETURN'  THEN st.qty
    ELSE 0 END),0) AS ledger_qty
FROM public.stock_items si
LEFT JOIN public.stock_transactions st ON st.stock_item_id = si.id
WHERE si.id='<STOCK_ITEM_ID>'::uuid
GROUP BY si.id, si.qty_on_hand;
```

**PASS:** `snapshot_qty == ledger_qty`.

#### KROK 6 — INSERT RECEIPT (idempotentnie)

> Uwaga: ten krok jest **write**. Wykonuj tylko, jeśli KROK 5 pokazuje mismatch.

```sql
BEGIN;

SELECT COUNT(*) AS already_exists
FROM public.stock_transactions
WHERE idempotency_key = 'E2E-RECEIPT-BACKFILL-001';

INSERT INTO public.stock_transactions (
  tenant_id,
  warehouse_id,
  part_id,
  stock_item_id,
  transaction_type,
  qty,
  uom,
  idempotency_key,
  created_by_user_id,
  created_by_username
)
SELECT
  '<TENANT_ID>'::uuid,
  '<WAREHOUSE_ID>'::uuid,
  '<PART_ID>'::uuid,
  '<STOCK_ITEM_ID>'::uuid,
  'RECEIPT',
  <QTY_RECEIPT>,
  'EA',
  'E2E-RECEIPT-BACKFILL-001',
  'system',
  'system'
WHERE NOT EXISTS (
  SELECT 1 FROM public.stock_transactions
  WHERE idempotency_key = 'E2E-RECEIPT-BACKFILL-001'
);

-- re-check
SELECT
  COALESCE(SUM(CASE
    WHEN transaction_type='RECEIPT' THEN qty
    WHEN transaction_type='ISSUE'   THEN -qty
    WHEN transaction_type='RETURN'  THEN qty
    ELSE 0 END),0) AS ledger_qty_after
FROM public.stock_transactions
WHERE stock_item_id='<STOCK_ITEM_ID>'::uuid;

COMMIT;
```

**PASS:** `ledger_qty_after` = `stock_items.qty_on_hand`.

### Audit fields on stock_items

Dla lepszej traceability dodano do `public.stock_items`:

- `created_at`, `updated_at`
- `created_by_user_id`, `created_by_username`
- trigger `trg_stock_items_touch_updated_at` (BEFORE UPDATE)

Wzorzec walidacji triggera bez trwałej zmiany (ROLLBACK):

```sql
BEGIN;

SELECT id, created_at, updated_at
FROM public.stock_items
WHERE id='<STOCK_ITEM_ID>'::uuid;

UPDATE public.stock_items
SET qty_reserved = qty_reserved
WHERE id='<STOCK_ITEM_ID>'::uuid
RETURNING id, created_at, updated_at;

ROLLBACK;
```

**PASS:** `updated_at` zmienia się w wyniku UPDATE, ale po `ROLLBACK` stan danych zostaje bez zmian.
