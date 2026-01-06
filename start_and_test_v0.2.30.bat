@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM AviationCAMO-MRO - One-click start + smoke test (v0.2.30)
REM For Windows / Project Owner friendly
REM ============================================================

set "COMPOSE_FILE=infra\docker\docker-compose.yml"
set "API_HEALTH_URL=http://localhost:8000/health"

echo.
echo [1/3] Starting stack (docker compose up -d --build)...
docker compose -f "%COMPOSE_FILE%" up -d --build
if errorlevel 1 (
  echo ERROR: docker compose failed.
  exit /b 2
)

echo.
echo [2/3] Waiting for API health...
REM Wait up to ~60s
set "OK=0"
for /l %%i in (1,1,30) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { $r=Invoke-WebRequest '%API_HEALTH_URL%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
  if not errorlevel 1 (
    set "OK=1"
    goto :HEALTH_OK
  )
  timeout /t 2 >nul
)

:HEALTH_OK
if "%OK%"=="0" (
  echo ERROR: API health did not become ready at %API_HEALTH_URL%
  echo Tip: run "docker compose -f %COMPOSE_FILE% ps" and check logs.
  exit /b 3
)

echo.
echo [3/3] OK - stack is up. Health:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest '%API_HEALTH_URL%' -UseBasicParsing | Select-Object -ExpandProperty Content"
echo.
echo Next: if you use Aircraft endpoints for the first time, run POST /v1/aircraft/_admin/bootstrap (Platform Admin).
echo.
exit /b 0
