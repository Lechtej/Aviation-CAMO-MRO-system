# Smoke test: Workforce (Employees)

## Scope
Validate Workforce module endpoints:
- `GET /v1/workforce/employees`
- `POST /v1/workforce/employees`
- `GET /v1/workforce/employees/{employee_id}`
- `PATCH /v1/workforce/employees/{employee_id}`

## Preconditions
- API container is running (`docker compose ps api`).
- Auth works and you can obtain an access token (Direct Grant) **or** you intentionally run in a dev mode that accepts unsigned tokens.
- For **PLATFORM_ADMIN** token you must pass explicit tenant header:
  - `X-Tenant-Id: <TENANT_UUID>`

## 1) Verify the contract source (critical)
The API serves OpenAPI using `/app/openapi.yaml` as the baseline.
If you add a router in code but forget to update **docs/02_api/openapi.yaml**, the endpoint may work but will **not** show up in `/openapi.json`.

**PASS:** `/openapi.json` contains `/v1/workforce/employees`.

```bash
curl -fsS http://127.0.0.1:8000/openapi.json | grep -n '"/v1/workforce/employees"'
```

## 2) Obtain token
Preferred on server:
```bash
cd /opt/aviationcamo/work/Aviation-CAMO-MRO-system
TOKEN="$(./get_token_dev.sh ./.env.local)"
echo "TOKEN_LEN=${#TOKEN}"
# PASS: >100
```

If `TOKEN_LEN=0`:
- verify Keycloak realm availability
- verify `.env.local` values
- check scripts are executable:
```bash
chmod +x ./scripts/smoke_auth.sh ./get_token_dev.sh
```

## 3) Roles endpoint quick check
```bash
curl -sS -o /dev/null -w "roles_http=%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/v1/roles
# expect: roles_http=200
```

## 4) List employees
```bash
TENANT_ID="00000000-0000-0000-0000-000000000000"

curl -sS -i \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  http://127.0.0.1:8000/v1/workforce/employees \
| sed -n '1,160p'

# expect: HTTP/1.1 200 and JSON: {"items": [...]}
```

## 5) Create employee
```bash
TENANT_ID="00000000-0000-0000-0000-000000000000"

curl -sS -i \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"employee_no":"E-0001","first_name":"Jan","last_name":"Kowalski","email":"jan.kowalski@example.com","phone":"+48100100200","is_active":true}' \
  http://127.0.0.1:8000/v1/workforce/employees \
| sed -n '1,200p'

# expect: HTTP/1.1 201 and payload with id
```

## 6) Get + patch employee
```bash
EMPLOYEE_ID="<UUID_FROM_CREATE>"
TENANT_ID="00000000-0000-0000-0000-000000000000"

curl -sS -o /dev/null -w "get_http=%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  http://127.0.0.1:8000/v1/workforce/employees/$EMPLOYEE_ID
# expect: get_http=200

curl -sS -i \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"phone":"+48111222333","is_active":false}' \
  http://127.0.0.1:8000/v1/workforce/employees/$EMPLOYEE_ID \
| sed -n '1,200p'
# expect: HTTP/1.1 200 and updated fields
```

## Failure modes
### 401 + `Missing bearer token`
- `$TOKEN` is empty (Direct Grant failed). Fix auth first.

### 404 Not Found
- router not included in `apps/api/src/main.py` or container not rebuilt.

### Endpoints work but OpenAPI doesn't show them
- `docs/02_api/openapi.yaml` missing Workforce paths; update YAML and rebuild the image.

### Crash on start: `ImportError: email-validator is not installed`
- Workforce schemas using `EmailStr` require `email-validator`.
- Add `email-validator>=2.0.0` to `apps/api/requirements.txt` and rebuild image.
