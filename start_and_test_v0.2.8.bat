@echo off
setlocal

REM ============================================================
REM Aviation CAMO/MRO - One-click start + smoke test (v0.2.8)
REM Robust batch syntax (no parenthesized IF blocks)
REM ============================================================

cd /d "%~dp0"
set "REPO_DIR=%cd%"
set "COMPOSE_FILE=%REPO_DIR%\infra\docker\docker-compose.yml"

set "API_BASE=http://localhost:8000"
set "KC_BASE=http://localhost:8080"
set "KC_REALM=aviation"
set "KC_TOKEN_URL=%KC_BASE%/realms/%KC_REALM%/protocol/openid-connect/token"
set "KC_WELLKNOWN=%KC_BASE%/realms/%KC_REALM%/.well-known/openid-configuration"

set "KC_CLIENT_ID=aviation-api"
set "KC_USERNAME=platformadmin"
set "KC_PASSWORD=platformadmin"

echo.
echo [0/7] Checking prerequisites...

where docker >nul 2>&1
if errorlevel 1 goto PREREQ_DOCKER

docker info >nul 2>&1
if errorlevel 1 goto PREREQ_ENGINE

if not exist "%COMPOSE_FILE%" goto PREREQ_COMPOSE

echo OK.

echo.
echo [1/7] Stopping existing stack (if any)...
docker compose -f "%COMPOSE_FILE%" down >nul 2>&1

echo.
echo [2/7] Starting stack (build)...
docker compose -f "%COMPOSE_FILE%" up -d --build
if errorlevel 1 goto FAIL_COMPOSE_UP

echo.
echo [3/7] Waiting for API /health (max 90s)...
call :WAIT_HTTP "%API_BASE%/health" 90
if errorlevel 1 goto FAIL_API_HEALTH

echo.
echo [4/7] Waiting for Keycloak well-known (max 120s)...
call :WAIT_HTTP "%KC_WELLKNOWN%" 120
if errorlevel 1 goto FAIL_KC_READY

echo.
echo [5/7] Getting token (platformadmin)...
set "ACCESS_TOKEN="
for /f "usebackq delims=" %%T in (`powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$body = 'client_id=%KC_CLIENT_ID%&grant_type=password&username=%KC_USERNAME%&password=%KC_PASSWORD%';" ^
  "$resp = Invoke-RestMethod -Method Post -ContentType 'application/x-www-form-urlencoded' -Body $body -TimeoutSec 60 -Uri '%KC_TOKEN_URL%';" ^
  "if ($null -eq $resp.access_token) { exit 2 } else { $resp.access_token }"`) do set "ACCESS_TOKEN=%%T"

if "%ACCESS_TOKEN%"=="" goto FAIL_TOKEN

echo Token OK.

echo.
echo [6/7] Calling /v1/tenants with Bearer token...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$hdr = @{ Authorization = ('Bearer ' + '%ACCESS_TOKEN%') };" ^
  "try { Invoke-RestMethod -Headers $hdr -Uri '%API_BASE%/v1/tenants' | ConvertTo-Json -Depth 10 } catch { " ^
  "  Write-Host 'ERROR calling /v1/tenants:'; " ^
  "  Write-Host $_.Exception.Message; " ^
  "  exit 3 " ^
  "}"
if errorlevel 1 goto FAIL_TENANTS

echo.

echo.
echo [7/7] Bootstrapping Logistics/Inventory (schema/tables/UoM)...
REM Calls admin bootstrap endpoint (requires PLATFORM_ADMIN)
for /f "delims=" %%B in ('powershell -NoProfile -Command ^
  "$headers=@{Authorization=('Bearer %TOKEN%'); 'X-Tenant-Id'='00000000-0000-0000-0000-000000000000'}; " ^
  + "try { (Invoke-RestMethod -Method Post -Uri '%API_BASE%/v1/logistics/_admin/bootstrap' -Headers $headers | ConvertTo-Json -Depth 10) } catch { $_.Exception.Message; exit 1 }"') do set "BOOTSTRAP_OUT=%%B"
echo %BOOTSTRAP_OUT%
if not "%BOOTSTRAP_OUT%"=="{  \"status\":  \"ok\"}" (
  REM non-fatal in case already bootstrapped
)

echo SUCCESS: Stack is up and RBAC check passed.
echo Open:
echo   API docs: %API_BASE%/docs
echo   Keycloak: %KC_BASE%  (realm: %KC_REALM%)
goto END_OK

:WAIT_HTTP
set "URL=%~1"
set "TIMEOUT=%~2"
set /a ELAPSED=0
:WAIT_LOOP
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri '%URL%'; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 exit /b 0
set /a ELAPSED+=3
if %ELAPSED% GEQ %TIMEOUT% exit /b 1
timeout /t 3 /nobreak >nul
goto WAIT_LOOP

:PREREQ_DOCKER
echo ERROR: Docker CLI not found. Install Docker Desktop.
goto END_FAIL

:PREREQ_ENGINE
echo ERROR: Docker Engine not reachable. Open Docker Desktop and wait for "Engine running".
goto END_FAIL

:PREREQ_COMPOSE
echo ERROR: Cannot find compose file:
echo   %COMPOSE_FILE%
echo Put this BAT in the repo root (folder that contains infra\).
goto END_FAIL

:FAIL_COMPOSE_UP
echo ERROR: docker compose up failed.
goto END_FAIL

:FAIL_API_HEALTH
echo ERROR: API did not become healthy. Last logs:
docker logs --tail 200 docker-api-1
goto END_FAIL

:FAIL_KC_READY
echo ERROR: Keycloak did not become ready. Last logs:
docker logs --tail 200 docker-keycloak-1
goto END_FAIL

:FAIL_TOKEN
echo ERROR: Could not obtain token. Last Keycloak logs:
docker logs --tail 200 docker-keycloak-1
goto END_FAIL

:FAIL_TENANTS
echo ERROR: /v1/tenants call failed. Last API logs:
docker logs --tail 200 docker-api-1
goto END_FAIL

:END_OK
echo.
echo --- Press any key to close ---
pause >nul
exit /b 0

:END_FAIL
echo.
echo --- Press any key to close ---
pause >nul
exit /b 1
