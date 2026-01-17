#!/usr/bin/env sh
set -eu

# Source of truth: OIDC_ISSUER pobieramy z dzialajacego kontenera API.
# Token wydrukowany na stdout (bez dodatkowych tekstow) -> latwe do uzycia w innych skryptach.

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
DOCKER_DIR="$ROOT_DIR/infra/docker"

# Prefer: docker compose ps -q api (dziala gdy compose projekt jest aktywny)
API_CID=""
if [ -d "$DOCKER_DIR" ]; then
  API_CID=$(cd "$DOCKER_DIR" && docker compose ps -q api 2>/dev/null | head -n 1 || true)
fi

# Fallback: znane nazwy
if [ -z "$API_CID" ]; then
  API_CID=$(docker ps -q --filter "name=docker-api-1" | head -n 1 || true)
fi
if [ -z "$API_CID" ]; then
  API_CID=$(docker ps -q --filter "name=api" | head -n 1 || true)
fi

if [ -z "$API_CID" ]; then
  echo "ERROR: API container not found. Run docker compose up -d (infra/docker)." 1>&2
  exit 2
fi

OIDC_ISSUER=$(docker exec -i "$API_CID" sh -lc 'printf %s "$OIDC_ISSUER"' 2>/dev/null || true)
if [ -z "$OIDC_ISSUER" ]; then
  echo "ERROR: OIDC_ISSUER is empty in API container env." 1>&2
  exit 3
fi

TOKEN_URL="$OIDC_ISSUER/protocol/openid-connect/token"

# Defaults zgodne z projektem (DEV)
CLIENT_ID=${CLIENT_ID:-aviation-api}
USERNAME=${KC_USERNAME:-platformadmin}
PASSWORD=${KC_PASSWORD:-qwe1234@#}

# Token JSON -> access_token
curl -sS -X POST \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=password" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  "$TOKEN_URL" \
| python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
