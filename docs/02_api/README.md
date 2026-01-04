# API Contract (OpenAPI)

File: `openapi.yaml`

## Tenant Context Rules
- Standard tenant users: tenant context resolved from OIDC token claims.
- Platform Admin: MAY provide `X-Tenant-Id` header for cross-tenant operations.

## Versioning
- API is versioned under `/v1/...`
- Contract changes recorded in `RELEASE_NOTES.md`
