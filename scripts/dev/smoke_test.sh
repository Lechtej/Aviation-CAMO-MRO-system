#!/usr/bin/env bash
set -euo pipefail

echo "[1/3] Starting docker compose..."
docker compose -f infra/docker/docker-compose.yml up -d --build

echo "[2/3] Checking API health..."
curl -fsS http://localhost:8000/health | cat
echo

echo "[3/3] Opening API docs..."
echo "Open in browser: http://localhost:8000/docs"
echo "Keycloak: http://localhost:8080 (realm: aviation)"
