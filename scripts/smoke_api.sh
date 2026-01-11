#!/usr/bin/env bash
set -euo pipefail

# Smoke API:
# 1) get token (via smoke_auth.sh)
# 2) GET /v1/roles must be 200
# 3) GET /v1/tenants must be 200
#
# Usage:
#   ./scripts/smoke_api.sh [.env.local] [API_BASE_URL override]
#
# Notes:
# - No X-Tenant-Id header (tenant inferred from token claims / routing).
# - Requires python3 (for token parsing, delegated to smoke_auth.sh).

ENV_FILE="${1:-.env.local}"
API_BASE_URL_OVERRIDE="${2:-}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: ENV file not found: $ENV_FILE"
  exit 2
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

API_BASE_URL="${API_BASE_URL_OVERRIDE:-${API_BASE_URL:-}}"
: "${API_BASE_URL:?API_BASE_URL missing (set in env or pass as 2nd arg)}"

token="$(bash ./scripts/smoke_auth.sh "$ENV_FILE")"
authz="Authorization: Bearer ${token}"

roles_code="$(curl -s -o /dev/null -w "%{http_code}" -H "$authz" "${API_BASE_URL%/}/v1/roles")"
if [[ "$roles_code" != "200" ]]; then
  echo "FAIL: /v1/roles expected 200, got ${roles_code}"
  exit 10
fi
echo "PASS: /v1/roles = 200"

tenants_code="$(curl -s -o /dev/null -w "%{http_code}" -H "$authz" "${API_BASE_URL%/}/v1/tenants")"
if [[ "$tenants_code" != "200" ]]; then
  echo "FAIL: /v1/tenants expected 200, got ${tenants_code}"
  exit 11
fi
echo "PASS: /v1/tenants = 200"
