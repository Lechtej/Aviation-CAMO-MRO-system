#!/usr/bin/env bash
set -euo pipefail

echo "[0/6] Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose plugin not found"; exit 1; }
echo "OK."

echo
echo "[1/6] Starting system (build)..."
docker compose up -d --build

echo
echo "[2/6] Waiting for services..."
sleep 5

echo
echo "[3/6] Health checks..."
curl -fsS http://localhost:8000/docs >/dev/null && echo "API OK" || { echo "API FAIL"; exit 1; }
curl -fsS http://localhost:3000 >/dev/null && echo "UI OK" || { echo "UI FAIL"; exit 1; }

echo
echo "[4/6] SYSTEM READY"
echo "UI:  http://localhost:3000"
echo "API: http://localhost:8000/docs"
