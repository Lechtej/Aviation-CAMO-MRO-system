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
