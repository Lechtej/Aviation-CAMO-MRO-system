@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM Aviation CAMO/MRO - One-click start + smoke test (v0.2.25)
REM KROK 14C: BAT hardening + diagnostics (Windows)
REM - DIAG mode via /diag or DIAG=1
REM - Unified exit codes
REM - Single SUMMARY at end
REM - Logs to .\logs
REM ============================================================

REM --- Args ---
set "DIAG=0"
if /I "%~1"=="/diag" set "DIAG=1"
if /I "%DIAG%"=="1" set "DIAG=1"

REM --- Defaults (single SUMMARY) ---
set "FINAL_RESULT=OK"
set "FINAL_CAUSE=All checks passed."
set "FINAL_EXIT_CODE=0"

REM --- Exit codes ---
set "EXIT_DOCKER_NOT_READY=10"
set "EXIT_BUILD_FAIL=20"
set "EXIT_API_HEALTH_TIMEOUT=30"
set "EXIT_KC_WELLKNOWN_TIMEOUT=40"
set "EXIT_TOKEN_FAIL=50"
set "EXIT_TENANTS_FAIL=60"

REM --- Paths ---
set "REPO_DIR=%~dp0"
set "COMPOSE_FILE=%REPO_DIR%infra\docker\docker-compose.yml"
set "LOG_DIR=%REPO_DIR%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\start_and_test_v0.2.25_%TS%.log"

REM --- Concurrency guard ---
set "LOCK_DIR=%LOG_DIR%\_run_lock"
if exist "%LOCK_DIR%" (
  call :LOG "ERROR: Another run seems active (lock exists): %LOCK_DIR%"
  call :FAIL "Another run is already active (lock exists)." 3
)
mkdir "%LOCK_DIR%" >nul 2>&1

REM --- Begin ---
call :LOG "Log saved to:"
call :LOG "  "%LOG_FILE%""

call :LOG ""
call :LOG "[0/7] Checking prerequisites..."

if not exist "%COMPOSE_FILE%" (
  call :FAIL "Compose file not found: %COMPOSE_FILE%" 2
)

where docker >nul 2>&1
if errorlevel 1 (
  call :FAIL "docker not found in PATH." 2
)

docker compose version >nul 2>&1
if errorlevel 1 (
  call :FAIL "docker compose not available (requires Docker Desktop / Compose v2)." 2
)

call :LOG "OK."

REM --- Optional DIAG pre-flight ---
if "%DIAG%"=="1" (
  call :LOG ""
  call :LOG "=== DIAG ==="
  powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%scripts\bat\run_diag.ps1" -ComposeFile "%COMPOSE_FILE%" -LogFile "%LOG_FILE%" -ApiPort 8000 -KeycloakPort 8080
  call :LOG "=== /DIAG ==="
)

REM --- Step 1: stop existing stack ---
call :LOG ""
call :LOG "[1/7] Stopping existing stack (if any)..."
docker compose -f "%COMPOSE_FILE%" down >>"%LOG_FILE%" 2>&1

REM --- Step 2: ensure Docker Engine is ready + start stack ---
call :LOG ""
call :LOG "[2/7] Starting stack (build)..."

call :WAIT_DOCKER_ENGINE 8 5
if errorlevel 1 (
  call :FAIL "Docker Engine did not become ready after retries." %EXIT_DOCKER_NOT_READY%
)

docker compose -f "%COMPOSE_FILE%" up -d --build >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :FAIL "docker compose up/build failed." %EXIT_BUILD_FAIL%
)

REM --- Step 3: API health ---
call :LOG ""
call :LOG "[3/7] Waiting for API /health (max 90s)..."
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%scripts\bat\http_wait.ps1" -Url "http://localhost:8000/health" -TimeoutSec 90 >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :FAIL "API /health timeout or not reachable." %EXIT_API_HEALTH_TIMEOUT%
)

REM --- Step 4: Keycloak well-known ---
call :LOG ""
call :LOG "[4/7] Waiting for Keycloak well-known (max 120s)..."
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%scripts\bat\http_wait.ps1" -Url "http://localhost:8080/realms/aviation/.well-known/openid-configuration" -TimeoutSec 120 >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :FAIL "Keycloak well-known timeout or not reachable." %EXIT_KC_WELLKNOWN_TIMEOUT%
)

REM --- Step 5: token ---
call :LOG ""
call :LOG "[5/7] Getting token (platformadmin)..."
set "ACCESS_TOKEN="
for /f "usebackq delims=" %%t in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%scripts\bat\kc_get_token.ps1" -KeycloakBase "http://localhost:8080" -Realm "aviation" -ClientId "aviation-api" -Username "platformadmin" -Password "platformadmin"`) do set "ACCESS_TOKEN=%%t"

if "%ACCESS_TOKEN%"=="" (
  call :FAIL "Token acquisition failed (empty token)." %EXIT_TOKEN_FAIL%
)
call :LOG "Token OK."

REM --- Step 6: tenants call ---
call :LOG ""
call :LOG "[6/7] Calling /v1/tenants with Bearer token..."
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_DIR%scripts\bat\api_get_with_bearer.ps1" -Url "http://localhost:8000/v1/tenants" -Token "%ACCESS_TOKEN%" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
  call :FAIL "/v1/tenants call failed (API auth/tenant pipeline)." %EXIT_TENANTS_FAIL%
)

call :LOG ""
call :LOG "SUCCESS."
goto :END

REM ============================================================
REM Helper functions
REM ============================================================

:WAIT_DOCKER_ENGINE
REM args: retries sleepSeconds
set "RETRIES=%~1"
set "SLEEP=%~2"
set /a N=0
:WAIT_DOCKER_LOOP
docker info >nul 2>&1
if not errorlevel 1 exit /b 0
set /a N+=1
if !N! GEQ %RETRIES% exit /b 1
timeout /t %SLEEP% /nobreak >nul
goto :WAIT_DOCKER_LOOP

:LOG
set "MSG=%~1"
echo(!MSG!
>>"%LOG_FILE%" echo(!MSG!
exit /b 0

:FAIL
REM args: cause exitcode
set "FINAL_RESULT=FAIL"
set "FINAL_CAUSE=%~1"
set "FINAL_EXIT_CODE=%~2"
goto :END

:END
rmdir "%LOCK_DIR%" >nul 2>&1

call :LOG ""
call :LOG "===== SUMMARY ====="
call :LOG "RESULT=%FINAL_RESULT%"
call :LOG "CAUSE=%FINAL_CAUSE%"
call :LOG "EXIT_CODE=%FINAL_EXIT_CODE%"
call :LOG "LOG_FILE=%LOG_FILE%"
call :LOG "--- Press any key to close ---"
pause >nul
exit /b %FINAL_EXIT_CODE%
