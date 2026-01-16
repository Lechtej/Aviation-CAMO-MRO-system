# Operacje (03_ops)

## Spis

- Deployment overview: `docs/03_ops/deployment.md`
- Production server rules: `docs/03_ops/SERVER_AND_DEPLOYMENT.md`
- Auth bootstrap: `docs/03_ops/SERVER_AUTH_BOOTSTRAP.md`
- Smoke tests:
  - Keycloak/OIDC: `docs/03_ops/SERVER_SMOKE_TEST_KEYCLOAK_OIDC.md`
  - Stock transactions: `docs/03_ops/SERVER_SMOKE_TEST_LOGISTICS_STOCK_TRANSACTIONS.md`
- DEV runtime note (API code shipped via image COPY) + recommended dev-only bind-mount: `docs/03_ops/DEV_DOCKER_BIND_MOUNT_MINI_TASK.md`


## Auth / OIDC – operacyjne testy i bootstrap

- (Brak wykrytych plików referencyjnych w ZIP)

Update 2026-01: pliki referencyjne istnieją i są linkowane wyżej (Auth bootstrap + smoke tests).

### Workforce
- `SERVER_SMOKE_TEST_WORKFORCE.md` — API smoke tests for workforce/employees (requires PLATFORM_ADMIN token + X-Tenant-Id)


## Workforce module
- `SERVER_SMOKE_TEST_WORKFORCE.md` — smoke tests for `/v1/workforce/*` and common failure modes (OpenAPI YAML vs runtime, missing deps, auth prerequisites).
