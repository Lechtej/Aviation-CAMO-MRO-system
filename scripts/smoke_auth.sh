#!/usr/bin/env bash
set -euo pipefail

# Smoke Auth: obtain access token via Direct Grant.
# Requirements:
# - .env file with: KC_BASE_URL, KC_REALM, OIDC_CLIENT_ID, OIDC_TEST_USERNAME, OIDC_TEST_PASSWORD
# - python3 available (used to parse JSON without jq)

ENV_FILE="${1:-.env.local}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: ENV file not found: $ENV_FILE"
  echo "Tip: copy .env.example -> .env.local (gitignored) and fill values."
  exit 2
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${KC_BASE_URL:?}"
: "${KC_REALM:?}"
: "${OIDC_CLIENT_ID:?}"
: "${OIDC_TEST_USERNAME:?}"
: "${OIDC_TEST_PASSWORD:?}"

TOKEN_URL="${KC_BASE_URL%/}/realms/${KC_REALM}/protocol/openid-connect/token"

resp="$(curl -fsS -X POST "$TOKEN_URL"   -H "Content-Type: application/x-www-form-urlencoded"   --data-urlencode "grant_type=password"   --data-urlencode "client_id=${OIDC_CLIENT_ID}"   --data-urlencode "username=${OIDC_TEST_USERNAME}"   --data-urlencode "password=${OIDC_TEST_PASSWORD}" )"

access_token="$(python3 -c 'import sys, json; print(json.load(sys.stdin).get("access_token",""))' <<<"$resp")"

if [[ -z "$access_token" ]]; then
  echo "ERROR: Empty access_token"
  echo "Raw response:"
  echo "$resp"
  exit 3
fi

echo "$access_token"
