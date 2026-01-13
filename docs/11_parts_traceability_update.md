
## #11.B – PARTS & TRACEABILITY – Update

### What was done
- Implemented idempotency handling for stock-transactions with replay semantics.
- Verified ledger vs snapshot consistency during concurrent ISSUE requests.
- Added replay path returning existing transaction payload instead of creating duplicates.

### Remaining tasks to close #11.B
- Enforce UNIQUE (tenant_id, idempotency_key) at DB level if not present.
- Add API-level guard: reject missing Idempotency-Key for mutating operations.
- Add E2E test: concurrent ISSUE with same key -> 201 + 200 replay.
- Documentation: describe idempotency contract and replay semantics.

(Added additively; no historical content removed.)

---

## 2026-01-13 — Wsad do kontynuacji #11.B (status + plan domknięcia)

### Zrobione (as-is)

- Zweryfikowano niespójność między snapshotem `stock_items.qty_on_hand` a ledgerem `stock_transactions`.
- Dodano pola audytowe oraz trigger `updated_at` dla `public.stock_items`.
- Wykonano idempotentny backfill `RECEIPT`, który wyrównał ledger do snapshotu.
- API: wprowadzono idempotency fast-check dla `POST /v1/logistics/stock-transactions`.
  - drugi request z tym samym `Idempotency-Key` zwraca `200 OK` i te same dane (REPLAY).
- API: zmieniono obsługę `IntegrityError` przy insercie `stock_transactions` na ścieżkę REPLAY → `200 OK`.

### Do domknięcia #11.B (konkret)

1) **Trwała reguła integralności (invariant)**
   - Snapshot nie może istnieć bez spójnego ledgeru (dla każdego `stock_item_id`: snapshot == suma ledger_delta).
   - Decyzja: gdzie wymuszamy invariant: **DB (constraint/trigger)** + **API (guard)**.

2) **Migracja DB**
   - Dodać/zweryfikować `UNIQUE (tenant_id, idempotency_key)` w `public.stock_transactions`.
   - Dodać mechanizm wymuszający invariant (trigger/constraint/check) i opisać ograniczenia (wydajność, batch import).

3) **Walidacja w API**
   - Guard: brak `Idempotency-Key` dla mutacji → `400`.
   - Guard: walidacja `qty` (min/max, decimal precision), tenant scoping.
   - Upewnić się, że replay działa identycznie dla `RECEIPT/ISSUE/RETURN`.

4) **Testy E2E**
   - Scenariusze: `RECEIPT`, `ISSUE`, `RETURN`.
   - Multi-tenant: ten sam key w różnych tenantach nie może kolidować.
   - Edge cases: `qty=0`, `qty<0`, duże qty, brak stocku, rounding/precision.

5) **Audyt endpointów stock-transactions**
   - Potwierdzić, że każdy punkt wejścia respektuje idempotency (fast-check + IntegrityError→REPLAY).
   - Upewnić się, że IntegrityError nie maskuje innych problemów (np. FK/NOT NULL) — tylko duplicate-key.

6) **Regresja modułów powiązanych**
   - Parts / StockItems / Locations / Warehouses: sprawdzić listowanie, filtrowanie, obliczenia stanów, brak side-effectów.

### Dokumentacja (to-do)

- Dopisać kontrakt idempotency: 201 vs 200 REPLAY, przykładowe payloady i expected responses.
- Opisać backfill RECEIPT (kiedy wolno, jak idempotentnie, jak walidować PASS).
- Opisać trigger `updated_at` i pola audytowe `stock_items`.

