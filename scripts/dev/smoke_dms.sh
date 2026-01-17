#!/usr/bin/env bash
set -euo pipefail

TENANT_ID="${1:-}"
if [[ -z "$TENANT_ID" ]]; then
  echo "Usage: $0 <TENANT_UUID>" >&2
  exit 2
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TOKEN="$("${SCRIPT_DIR}/get_token_dev.sh")"

echo "== DMS smoke =="
echo "BASE_URL=${BASE_URL}"
echo "TENANT_ID=${TENANT_ID}"
echo

call() {
  local path="$1"
  echo "-- GET ${path}"
  local resp http
  resp="$(mktemp)"
  http="$(curl -sS -o "${resp}" -w "%{http_code}"     -H "Authorization: Bearer ${TOKEN}"     -H "X-Tenant-ID: ${TENANT_ID}"     "${BASE_URL}${path}")"
  echo "HTTP ${http}"
  cat "${resp}"
  echo
  rm -f "${resp}"

  if [[ "${http}" != "200" ]]; then
    echo "FAIL: ${path} returned HTTP ${http}" >&2
    return 1
  fi
}

call "/v1/dms/types"
call "/v1/dms/documents"

echo "PASS: DMS smoke OK"
