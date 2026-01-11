#!/usr/bin/env bash
set -euo pipefail

# Deterministic local bootstrap:
# - start docker compose
# - wait for Keycloak + API
# - (optional) call POST /v1/admin/bootstrap (seed)
# - run smoke tests
#
# Usage:
#   ./scripts/bootstrap_local.sh [.env.local]

ENV_FILE="${1:-.env.local}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: ENV file not found: $ENV_FILE"
  echo "Tip: copy .env.example -> .env.local (gitignored) and fill values."
  exit 2
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${API_BASE_URL:?}"
: "${KC_BASE_URL:?}"
: "${KC_REALM:?}"

echo "[1/5] docker compose up -d"
docker compose -f infra/docker/docker-compose.yml up -d --build

echo "[2/5] wait for Keycloak realm"
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" "${KC_BASE_URL%/}/realms/${KC_REALM}")" || true
  if [[ "$code" == "200" || "$code" == "302" ]]; then
    echo "PASS: Keycloak reachable (${code})"
    break
  fi
  sleep 1
  if [[ "$i" == "60" ]]; then
    echo "FAIL: Keycloak not reachable (last code: ${code})"
    exit 20
  fi
done

echo "[3/5] wait for API health"
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL%/}/health")" || true
  if [[ "$code" == "200" ]]; then
    echo "PASS: API health = 200"
    break
  fi
  sleep 1
  if [[ "$i" == "60" ]]; then
    echo "FAIL: API health not reachable (last code: ${code})"
    exit 21
  fi
done

echo "[4/5] optional seed: POST /v1/admin/bootstrap (requires token + admin rights)"
if [[ "${RUN_API_BOOTSTRAP:-0}" == "1" ]]; then
  token="$(bash ./scripts/smoke_auth.sh "$ENV_FILE")"
  authz="Authorization: Bearer ${token}"
  bootstrap_code="$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$authz" "${API_BASE_URL%/}/v1/admin/bootstrap")"
  if [[ "$bootstrap_code" != "200" && "$bootstrap_code" != "201" && "$bootstrap_code" != "204" ]]; then
    echo "FAIL: /v1/admin/bootstrap expected 200/201/204, got ${bootstrap_code}"
    exit 30
  fi
  echo "PASS: /v1/admin/bootstrap (${bootstrap_code})"
else
  echo "SKIP: RUN_API_BOOTSTRAP != 1"
fi

echo "[5/5] smoke tests"
bash ./scripts/smoke_api.sh "$ENV_FILE"
echo "DONE"
