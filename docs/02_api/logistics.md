## Update: RBAC for POST /v1/logistics/stock-transactions (Epic #10.1)

**Scope**
Adds role-based access control to stock transactions by transaction type, enforced server-side before business logic.

**Endpoint**
- `POST /v1/logistics/stock-transactions`

**Transaction types**
- `RECEIPT`
- `ISSUE`
- `RETURN`

**Effective roles (Keycloak → API)**
- Store / Logistics: `LOGISTICS_OFFICER`
- Mechanic: `MECHANIC`
- CAMO Planner: `CAMO_PLANNER`
- Admins: `PLATFORM_ADMIN`, `TENANT_ADMIN`

**Authorization matrix**
- `RECEIPT`: `LOGISTICS_OFFICER` (admins allowed)
- `ISSUE`: `LOGISTICS_OFFICER` or `MECHANIC`
  - `CAMO_PLANNER`: **only with reservation** (future field; currently denied)
- `RETURN`: `LOGISTICS_OFFICER` or `MECHANIC`
- Admins: full access

**Enforcement**
- Guard executes **before** stock mutation.
- Missing role → `403`.
- Invalid type → `422`.

**DEV/runtime note**
API container runs code from image path `/app`. Any host-side code changes require
`docker compose build --no-cache api` (no bind-mount in DEV).

Recommendation (post #10.1): introduce a DEV-only bind-mount override so `apps/api/src` is mounted into `/app`.
See `docs/03_ops/DEV_DOCKER_BIND_MOUNT_MINI_TASK.md`.

**Verification (curl)**
Validated with black-and-white tests:
- MECH + RECEIPT → 403
- MECH + ISSUE → 201
- STORE + RECEIPT → 201
- CAMO + ISSUE (no reservation) → 403

---

## 2026-01-12 — Stock ledger vs snapshot (data integrity) + audit fields

### Problem observed

W trakcie E2E testów (ISSUE/RETURN) wykryto niespójność:

- `stock_items.qty_on_hand` (snapshot) = **8.000**
- suma z `stock_transactions` (ledger) dla tego samego `stock_item_id` = **-2.000**

To oznacza, że *brakuje transakcji bazowej* (np. RECEIPT/initial receipt), która tłumaczy stan początkowy.

### Invariant (wymaganie systemowe)

Dla każdego `stock_item_id`:

- `stock_items.qty_on_hand` **MUSI** równać się `SUM(ledger_delta)` z `stock_transactions`, gdzie:
  - `RECEIPT` = `+qty`
  - `ISSUE` = `-qty`
  - `RETURN` = `+qty`

> Ten invariant to podstawa audytu i traceability. Jeśli jest łamany, to nie da się ufać ani snapshotowi, ani transakcjom.

### Konsekwencje (jeśli invariant nie jest pilnowany)

- audyt: brak możliwości wyjaśnienia „skąd się wzięło 8 sztuk”,
- integracje: UI/API pokazuje stan nie do odtworzenia z historii,
- ryzyko błędów kosztowych (cost entries) i błędów w rezerwacjach.

### Minimalna naprawa (doraźna) — backfill RECEIPT

Jeśli snapshot jest poprawny, a ledger nie ma transakcji bazowej, dopuszczamy **jednorazowy backfill** w formie `RECEIPT` z **idempotency**.

**Ważne:** `stock_transactions` ma NOT NULL dla pól audytu/tenant/warehouse/part/uom.

Przykładowy INSERT (dla konkretnego stock_item):

```sql
BEGIN;

-- 0) Idempotency guard
SELECT COUNT(*) AS already_exists
FROM public.stock_transactions
WHERE idempotency_key = 'E2E-RECEIPT-BACKFILL-001';

-- 1) Insert (wypełnij wszystkie NOT NULL)
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
  <QTY>::numeric,
  'EA',
  'E2E-RECEIPT-BACKFILL-001',
  'system',
  'system'
WHERE NOT EXISTS (
  SELECT 1
  FROM public.stock_transactions
  WHERE idempotency_key = 'E2E-RECEIPT-BACKFILL-001'
);

-- 2) Walidacja
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

COMMIT;
```

### `stock_items` — minimalne pola audytu

Dla `stock_items` (snapshot) brakowało pola czasu utworzenia/aktualizacji → utrudniało traceability.
Wprowadzono minimalne pola:

- `created_at` (timestamptz, default `now()`)
- `updated_at` (timestamptz, default `now()` + trigger)
- `created_by_user_id` (text, default `'system'`)
- `created_by_username` (text, nullable)

### Docelowa naprawa (wątek B)

- przenieść *źródło prawdy* do ledgera (snapshot jako pochodna),
- wprowadzić kontrolę spójności (np. constraint/materialized check) + testy E2E,
- zdefiniować „initial stock load” jako jawny proces (RECEIPT z `source_ref_type='INITIAL_LOAD'`),
- rozważyć tenant-scoping `stock_items` (aktualnie tenant jest w ledgerze).

---

## 2026-01-13 — Stock-transactions: idempotency contract + REPLAY on duplicates

### Contract (client-visible)

For `POST /v1/logistics/stock-transactions` the API supports idempotent writes using header:

- `Idempotency-Key: <string>`

Expected behavior per tenant:

- **First request** with a new key → `201 Created` and a JSON body containing the created transaction.
- **Replay request** with the same key (same tenant) → `200 OK` and **the same JSON body** as the first request.
- No additional stock mutation occurs on replay.

### Implementation notes (server-side)

- DB should enforce uniqueness for the idempotency key (recommended): `UNIQUE (tenant_id, idempotency_key)`.
- Insert path catches duplicate-key `IntegrityError` and resolves it as **REPLAY → 200** by reading the existing transaction and returning it.
- API should treat missing `Idempotency-Key` as invalid for mutating operations (recommended guard): `400` with a clear message.

### Example (ISSUE)

Request (new key):

```bash
curl -sS -i -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Idempotency-Key: E2E-IDEMP-ISSUE-001" \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/v1/logistics/stock-transactions" \
  --data '{"type":"ISSUE","stock_item_id":"__UUID__","qty":1}'
```

Response:
- `201 Created` with transaction payload.

Repeat the same request (same key):
- `200 OK` (REPLAY) with identical payload.

## Update #13 — Stock Reservations (soft lock)

This release adds a **reservation layer** for CAMO/Stores flows without changing on-hand stock at reservation time.

**DB / Ledger**
- Migration `db/migrations/public/0005_public_stock_reservations.sql` introduces `public.stock_reservations` (tenant isolated by `tenant_id`).
- `public.stock_transactions` gets optional `reservation_id` FK for traceability (e.g., CAMO ISSUE must reference a reservation).

**API**
- `GET /v1/logistics/stock-reservations` — list last 200 reservations for the tenant (roles: LOGISTICS_OFFICER, CAMO_PLANNER, or ADMIN).
- `POST /v1/logistics/stock-reservations` — create reservation and increment `stock_items.qty_reserved` atomically.
- `POST /v1/logistics/stock-transactions` — for `ISSUE` by `CAMO_PLANNER`, `reservation_id` is required (enforced in RBAC gate).

**Tenant header safety**
- Tenant resolution middleware now guards invalid tenant UUID values and returns `400 Invalid X-Tenant-Id (expected UUID)` instead of crashing the API process.

---

## Schema note (current)

For now, Logistics stock tables are created in **public** schema:
- `public.stock_items`
- `public.stock_reservations`
- `public.stock_transactions`

Tenant isolation is enforced at API level (required `X-Tenant-Id` header + `tenant_id` in reservation/transaction rows).
If you query the DB directly, always filter by `tenant_id`.

Planned (later): move Logistics stock tables into tenant schemas (e.g. `t_lot.*`) once cross-tenant bootstrap + migrations are ready.


---

## Update: Stock Reservations E2E (Epic #13)

**Zakres**
- Endpoint: `POST /v1/logistics/stock-reservations`
- Integracja z `ISSUE` w `POST /v1/logistics/stock-transactions`
- Spójność snapshot ↔ ledger (`qty_reserved`)

**Zmiany kluczowe**
- Rezerwacje zapisywane bezpośrednio do `public.stock_reservations` (SQL INSERT).
- **Jawny `db.commit()` po INSERT rezerwacji** – zapobiega rollbackowi na zamknięciu sesji.
- Snapshot `stock_items.qty_reserved` liczony wyłącznie z ledgeru rezerwacji:
  - `recalc_qty_reserved()` po INSERT i po CONSUME.
- Walidacje ISSUE:
  - rezerwacja istnieje, `OPEN`, nieprzeterminowana
  - `qty <= (qty_reserved - qty_consumed)`
  - zgodność `stock_item_id`

**Ryzyka / wnioski**
- Krótki TTL tokenów OIDC powoduje 401 w długich testach CLI.
  - Rekomendacja: helper `auth_smoke_test.sh` lub automatyczny refresh.
