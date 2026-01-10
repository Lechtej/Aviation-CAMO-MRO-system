# PO Summary – Production Server & Delivery Process

## What was achieved
- Production environment access is now **secure** and **repeatable**.
- We eliminated reliance on the Hetzner web console (which caused copy/paste command corruption).
- SSH is hardened to **key-only** authentication.

## Why it matters (business impact)
- Lower risk of production outages caused by manual command entry errors.
- Faster onboarding for new engineers/testers (clear rules: where to do what).
- A foundation for future auditability (who changed what, when, and through which repo commit).

## How releases are delivered (high-level)
1. DEV makes changes locally and commits to GitHub.
2. On production server (SSH): `git pull`.
3. Containers are updated via `docker compose up -d`.
4. Verification is done via browser (Keycloak UI / API docs).

## Rules (non-negotiable)
- No production hotfixes without a commit.
- No password logins to production.
- External testers get separate users (no root access).


---
## ADDENDUM 2026-01 – PROD Auth & Multi-Tenancy (B1)

- Schema-per-tenant model **B1** adopted.
- Central ACL: `public.aircraft_mro_access`.
- `public.tenants.schema_name` is routing key.
- Keycloak is source of roles; DB maps permissions.
- `tenant_id` claim mandatory in access token (PROD).
