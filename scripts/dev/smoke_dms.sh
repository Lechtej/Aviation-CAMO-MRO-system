#!/usr/bin/env sh
set -eu

TENANT_ID=${1:-}
if [ -z "$TENANT_ID" ]; then
  echo "Usage: $0 <TENANT_UUID>" 1>&2
  exit 2
fi

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
TOKEN=$("$ROOT_DIR/scripts/dev/get_token_dev.sh")

# API base: override env if needed.
# Server: zwykle http://localhost:8000 (host) albo https://api.forgemotionsystems.com
API_BASE=${API_BASE:-http://localhost:8000}

req() {
  path=$1
  echo "==> GET $path"
  # Print HTTP status + body (first 2000 chars)
  # -D - prints headers; sed trims noisy headers if needed by caller
  curl -sS -D - \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: $TENANT_ID" \
    "$API_BASE$path" \
  | sed -n '1,200p'
  echo ""
}

echo "[SMOKE DMS] tenant=$TENANT_ID api=$API_BASE"
req "/v1/dms/types"
req "/v1/dms/documents"
