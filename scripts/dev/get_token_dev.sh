#!/usr/bin/env bash
set -euo pipefail

# Source of truth: read issuer from running API container env
API_CONTAINER="${API_CONTAINER:-docker-api-1}"
DOCKER_PROJECT_DIR="${DOCKER_PROJECT_DIR:-/opt/aviationcamo/Aviation-CAMO-MRO-system/infra/docker}"

# Keycloak credentials (project convention)
KC_CLIENT_ID="${KC_CLIENT_ID:-aviation-api}"
KC_USERNAME="${KC_USERNAME:-platformadmin}"
KC_PASSWORD="${KC_PASSWORD:-qwe1234@#}"

cd "$DOCKER_PROJECT_DIR"
OIDC_ISSUER="$(docker exec -i "$API_CONTAINER" sh -lc 'printf "%s" "$OIDC_ISSUER"')"

if [[ -z "${OIDC_ISSUER}" ]]; then
  echo "ERROR: OIDC_ISSUER is empty in API container ($API_CONTAINER)." >&2
  exit 2
fi

TOKEN_URL="${OIDC_ISSUER%/}/protocol/openid-connect/token"

ACCESS_TOKEN="$(
  curl -sS -X POST     --data-urlencode "client_id=${KC_CLIENT_ID}"     --data-urlencode "grant_type=password"     --data-urlencode "username=${KC_USERNAME}"     --data-urlencode "password=${KC_PASSWORD}"     "${TOKEN_URL}"   | python3 - <<'PY'
import sys, json
data = json.load(sys.stdin)
tok = data.get("access_token")
if not tok:
    print("ERROR: access_token missing. Response keys:", sorted(data.keys()), file=sys.stderr)
    print(json.dumps(data, indent=2), file=sys.stderr)
    raise SystemExit(3)
print(tok)
PY
)"

echo "${ACCESS_TOKEN}"
