# ADR-008: Tenant Feature Flags + Admin Console scope

Status: **Accepted (design-only)**  
Date: **2026-01-11**  
Owner: Platform / Architecture

## Context
System jest multi-tenant (schema-per-tenant). Różne tenanty mogą wymagać różnych modułów (np. LOTAMS vs LST).
Potrzebujemy mechanizmu włączania/wyłączania funkcji **per tenant** bez reworku i bez uzależniania się od konfiguracji Keycloak.

## Decision
1. Wprowadzamy **Tenant Feature Flags** jako przełączniki funkcjonalności per tenant.
2. Źródło prawdy: **DB** (nie Keycloak).
3. Egzekucja:
   - **API**: obowiązkowo (blokada endpointów),
   - **Worker/Jobs**: obowiązkowo (skip/no-op),
   - **UI**: opcjonalnie (UX, bez zaufania).
4. Semantyka: feature OFF → **HTTP 403** z kodem domenowym `FEATURE_DISABLED`.
5. Wprowadzamy minimalny audyt zmian.

## Data Model (MVP)
### `public.feature_flags`
- `key TEXT PK`
- `name TEXT NOT NULL`
- `description TEXT NULL`
- `default_enabled BOOLEAN NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`

### `public.tenant_feature_flags`
- `id UUID PK`
- `tenant_id UUID FK -> public.tenants(id)`
- `feature_key TEXT FK -> feature_flags(key)`
- `enabled BOOLEAN NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `updated_by TEXT NULL` (subject/user id)
- UNIQUE `(tenant_id, feature_key)`

Resolution:
- jeśli istnieje override `(tenant_id, feature_key)` → użyj `enabled`
- inaczej → `feature_flags.default_enabled`

### Audit (MVP)
`public.tenant_feature_flag_audit(tenant_id, feature_key, old_value, new_value, changed_at, changed_by, reason)`

## Feature keys (minimalny zestaw)
- `stores.enabled` (master switch dla magazynu)
- `epic1.work_orders`
- `epic4.crs`
- `epic3.replenishment` (zależny od `stores.enabled`)

## Consequences
### Pros
- Niezależność od zewnętrznej konfiguracji (Keycloak).
- Spójna egzekucja na API + worker (brak „połowicznych” funkcji).
- Audytowalność zmian (kto, kiedy, co przełączył).

### Cons / Risks
- Ryzyko „częstych odczytów” → wymagany cache TTL (30–60s) + best-effort invalidacja po zmianie.
- Wymaga standaryzacji błędów (`FEATURE_DISABLED`) w API.

## Implementation notes (non-binding)
- Guard per router/prefix (np. `/stores/*` zależne od `stores.enabled`).
- Jobs: weryfikacja flagi na wejściu i log `skipped`.
