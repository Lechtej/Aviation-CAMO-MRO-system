# PO – Production access & workflow

## What changed
We moved away from the Hetzner web console and introduced a **secure, repeatable production workflow**.

## Production access (safe by design)
- Production server is accessible via **SSH key only**
- Password login is **disabled**
- This reduces brute-force risk and accidental mistakes

## Who does what
- **Developers (local repo):** implement changes, commit to GitHub
- **Ops (SSH):** only pull and restart containers (no manual edits)
- **Browser UI:** Keycloak and API testing

## Why it matters
- Lower production risk
- Faster onboarding of new contributors
- Changes are auditable and repeatable
- Safe foundation for onboarding external testers

## Next steps
1. Create a dedicated `tester` user (SSH key, limited permissions)
2. Standardize docker-compose production deployment
3. Finish FastAPI ↔ Keycloak (OIDC) integration end-to-end
4. Add reverse proxy / HTTPS for public access


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).

---
## ADDENDUM 2026-01-11 — What a PO can validate in the browser (no CLI)

**Preconditions:**
- UI: `https://app.forgemotionsystems.com`
- Auth: `https://auth.forgemotionsystems.com`
- API: `https://api.forgemotionsystems.com`

**Happy path validation (PO):**
1. Open UI and press **Login** → Keycloak login page must open.
2. Login with a test user (e.g. `camo_user`).
3. UI shows username (top-right) and **Logout** button.
4. `CAMO / Aircraft` should load list (HTTP 200). If it fails:
   - verify API base URL is `https://api.forgemotionsystems.com`
   - verify user has required role (`CAMO_*`)
   - verify tenant routing (see ops note: debug header vs token claim)

**Important limitation (current E2E bootstrap):**
- Tenant routing may be temporarily provided by a debug header during early tests.
- Final PROD contract is `tenant_id` claim in the access token.

## ADDENDUM 2026-01-11 — Tenant routing prerequisites for UI workflows

To make UI workflows behave correctly in multi-tenant mode:
- User must authenticate via Keycloak (OIDC code + PKCE).
- API must resolve tenant context per request (see `docs/02_api/TENANT_CONTEXT.md`).
- For early E2E/demo, a debug tenant header can be used **only** when explicitly enabled (`DEBUG_TENANT_HEADER=true`).

Acceptance check for Product / PO:
- After login, user sees data belonging to the selected tenant (e.g. Aircraft list).
- Switching tenant (admin/debug) changes the dataset returned by API (verified via `X-Tenant-Schema`).

## ADDENDUM 2026-01-11 — tenant context + UI login constraints

### Co PO powinien wiedzieć (z perspektywy akceptacji E2E)

- System jest multi-tenant: ten sam endpoint API zwraca inne dane zależnie od tenant context.
- W MVP tenant context może być podawany mechanizmem debug (`X-Debug-Tenant-Id`) – to jest tryb demonstracyjny.
- Docelowo tenant jest rozpoznawany z tokena (`tenant_id` claim) – to jest tryb produkcyjny.

### Objawy błędnej konfiguracji

- Login w UI kończy się ekranem błędu Keycloak: `Invalid parameter: redirect_uri` → brak klienta UI lub redirect URI.
- UI pokazuje `Failed to fetch` mimo "API: OK" → CORS / base URL / brak dostępu do API.

## ADDENDUM 2026-01-11 - Tenant context for PO/UAT

W srodowisku UAT/dev (E2E) mozliwe jest wymuszenie tenant context przez header `X-Debug-Tenant-Id`.
Dla PO oznacza to, ze podczas testow UI zawsze pracuje w jednym, jawnie wskazanym tencie (np. `t_aca`).
W produkcji docelowo tenant jest ustalany z tokena (claim `tenant_id`) i uzytkownik nie powinien miec mozliwosci zmiany tenantow bez roli `PLATFORM_ADMIN`.

## ADDENDUM 2026-01-11 - Tenant context as a product requirement

W MVP (B1) tenant context jest krytycznym wymaganiem produktowym - bez niego użytkownik nie zobaczy danych.

Wnioski dla PO:
* Każdy user UI musi mieć jednoznacznie określony tenant (docelowo claim `tenant_id`).
* Jeżeli w środowisku demo używamy `X-Debug-Tenant-Id`, to jest to **tylko workaround techniczny**, a nie zachowanie produkcyjne.
* UI nawigacja opiera się o role realm (`realm_access.roles`), ale dane zawsze filtruje backend po tenant context.
