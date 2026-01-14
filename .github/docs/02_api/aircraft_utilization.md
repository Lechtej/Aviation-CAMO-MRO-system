# Aircraft utilization (FH/FC) — API contract (public)

## Scope
Tracking aircraft utilization as an **append-only ledger** (flight hours / flight cycles) with a **counters snapshot** for fast reads and planning.

## Tables (public)
- `public.aircraft_utilization_ledger`
- `public.aircraft_counters`
- `public.aircraft` (extended with optional dates)

## Endpoints

### Add utilization entry (append-only)
`POST /v1/aircraft/{aircraft_id}/utilization`

**Body**
```json
{
  "op_date": "2026-01-14",
  "delta_fh": 3.50,
  "delta_fc": 2,
  "source": "MANUAL",
  "source_ref": "logbook:2026-01-14:LO1234",
  "notes": "daily ops"
}
```

**Rules**
- `delta_fh >= 0`, `delta_fc >= 0`
- Uniqueness:
  - if `source_ref` provided: unique `(aircraft_id, source, source_ref)`
  - else: unique `(aircraft_id, op_date, source)`

**Response**
- created ledger entry (includes `id`, `aircraft_id`, `created_at`)

### List utilization entries
`GET /v1/aircraft/{aircraft_id}/utilization`

Returns ledger entries ordered by `op_date DESC, created_at DESC`.

### Get counters snapshot
`GET /v1/aircraft/{aircraft_id}/counters`

Returns:
- `total_fh`, `total_fc` (non-negative)
- `updated_at`

If counters row is missing, API creates it with zeros on first call.

## Notes
- "Age" is derived from `manufacture_date` / `entry_into_service_date` (no separate field needed).
- Forecasting/maintenance program will consume `total_fh/total_fc` + accomplishments in next steps.
