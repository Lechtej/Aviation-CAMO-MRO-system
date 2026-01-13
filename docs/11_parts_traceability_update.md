
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
