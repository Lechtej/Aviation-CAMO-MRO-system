# PGL Fleet Import (v0.2.3)

Source of truth:
- `db/import/source/Floty_MRO_PGL_v1.1.1_FINAL.xlsx`
  - Full fleet is in sheet **Fleet_ALL** (929 rows; 316 LOTAMS; 613 LST; 0 unknown)

Columns expected in Fleet_ALL:
```
MRO, Airline, Airline_IATA, Airline_ICAO, Manufacturer, Type, Subtype, Model,
Registration, MSN, SourceURL, RetrievedAtUTC
```

## Data identity rules
- `Registration` is treated as the current unique aircraft key for this dataset (929 unique).
- `MSN` is optional and missing for ~466 rows; when present it is stored and can be used later for history/merge.

## Run import
1. Run migrations + seed core tenants (PGL / LOTAMS / LST / LOT)
2. Generate CSV exports from XLSX and import into Postgres.

Use:
- `db/import/run_import.bat` (Windows) or run commands from the README below.

## Verification (must pass)
- Total aircraft: 929
- Aircraft MRO mapping rows: 929 (from this dataset)
- LOTAMS: 316
- LST: 613
- Unknown: 0

See `db/import/scripts/verify_import.sql`.
