@echo off

setlocal




REM ============================================================
REM DIAGNOSTICS MODE
REM - Enable via env var: DIAG=1
REM - Or run: start_and_test_v0.2.12.bat /diag
REM ============================================================

if /I "%~1"=="/diag" set "DIAG=1"
if /I "%~1"=="-diag" set "DIAG=1"
if not defined DIAG set "DIAG=0"

REM ============================================================

REM Aviation CAMO/MRO - One-click start + smoke test (v0.2.12)

REM Robust batch syntax (no parenthesized IF blocks)

REM ============================================================



cd /d "%~dp0"

set "REPO_DIR=%cd%"

set "COMPOSE_FILE=%REPO_DIR%\infra\docker\docker-compose.yml"



REM --- Logging ---

set "LOG_DIR=%REPO_DIR%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

set "LOG_FILE=%LOG_DIR%\start_and_test_v0.2.12_%TS%.log"

REM ============================================================
REM RESULT / SUMMARY STATE
REM ============================================================
set "RESULT=FAIL"
set "FAIL_REASON=Unknown failure"
set "EXIT_CODE=1"


echo.

echo Log saved to:

echo   "%LOG_FILE%"

echo ===== START %date% %time% =====>>"%LOG_FILE%"

echo REPO_DIR=%REPO_DIR%>>"%LOG_FILE%"

echo COMPOSE_FILE=%COMPOSE_FILE%>>"%LOG_FILE%"





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



REM Check Docker Engine (retry/wait)

docker info >nul 2>&1

if errorlevel 1 call :WAIT_DOCKER_ENGINE

docker info >nul 2>&1

if errorlevel 1 goto PREREQ_ENGINE



if not exist "%COMPOSE_FILE%" goto PREREQ_COMPOSE



echo OK.



echo.

REM ============================================================
REM Optional diagnostics snapshot BEFORE changing anything
REM ============================================================
if "%DIAG%"=="1" call :DIAG_SECTION

echo [1/7] Stopping existing stack (if any)...

docker compose -f "%COMPOSE_FILE%" down >>"%LOG_FILE%" 2>&1



echo.

echo [2/7] Starting stack (build)...

docker compose -f "%COMPOSE_FILE%" up -d --build >>"%LOG_FILE%" 2>&1

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

  "if ($null -eq $resp.access_token) { exit 2 } else { ($resp.access_token.ToString().Trim()) }"`) do set "ACCESS_TOKEN=%%T"



if "%ACCESS_TOKEN%"=="" goto FAIL_TOKEN



echo Token OK.



echo.

echo [6/7] Calling /v1/tenants with Bearer token...


set "BEARER_TOKEN=%ACCESS_TOKEN%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\call_tenants.ps1" -ApiBase "%API_BASE%" > "%LOG_DIR%\tenants.json" 2>> "%LOG_FILE%"
if errorlevel 1 (
  echo ERROR: /v1/tenants call failed. Last API logs: 
  docker compose logs --no-color --tail 80 api >> "%LOG_FILE%" 2>&1
  goto FAIL_TENANTS
)
type "%LOG_DIR%\tenants.json"



echo.



echo.

echo [7/7] Bootstrapping Logistics/Inventory (schema/tables/UoM)...

REM Calls admin bootstrap endpoint (requires PLATFORM_ADMIN)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\call_bootstrap.ps1" -ApiBase "%API_BASE%" > "%LOG_DIR%\bootstrap.json" 2>> "%LOG_FILE%"
if errorlevel 1 goto FAIL_BOOTSTRAP
set "BOOTSTRAP_OUT="
for /f "usebackq delims=" %%B in (`type "%LOG_DIR%\bootstrap.json"`) do set "BOOTSTRAP_OUT=%%B"
echo %BOOTSTRAP_OUT%

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



:WAIT_DOCKER_ENGINE

set "RETRIES=10"

set "SLEEP=5"

echo Docker Engine not ready - waiting (up to %RETRIES% attempts, %SLEEP%s each)...

echo Docker Engine not ready - waiting (up to %RETRIES% attempts, %SLEEP%s each)...>>"%LOG_FILE%"

set /a i=0

:WAIT_DOCKER_ENGINE_LOOP

set /a i+=1

docker info >nul 2>&1

if not errorlevel 1 goto WAIT_DOCKER_ENGINE_OK

echo   attempt %i%/%RETRIES% ...

echo   attempt %i%/%RETRIES% ...>>"%LOG_FILE%"

if %i% GEQ %RETRIES% goto WAIT_DOCKER_ENGINE_END

timeout /t %SLEEP% /nobreak >nul

goto WAIT_DOCKER_ENGINE_LOOP

:WAIT_DOCKER_ENGINE_OK

echo Docker Engine is running.

echo Docker Engine is running.>>"%LOG_FILE%"

goto :eof

:WAIT_DOCKER_ENGINE_END

echo Docker Engine still not reachable after retries.

echo Docker Engine still not reachable after retries.>>"%LOG_FILE%"

goto :eof



:PREREQ_DOCKER
set "FAIL_REASON=Docker CLI not found (Docker Desktop not installed or not on PATH)."
set "EXIT_CODE=10"
echo ERROR: Docker CLI not found. Install Docker Desktop.

goto END_FAIL



:PREREQ_ENGINE
set "FAIL_REASON=Docker Engine not ready after retries."
set "EXIT_CODE=10"
echo ERROR: Docker Engine not reachable. Open Docker Desktop and wait for "Engine running".

goto END_FAIL



:PREREQ_COMPOSE
set "FAIL_REASON=docker-compose.yml not found (bad path or incomplete ZIP)."
set "EXIT_CODE=13"
echo ERROR: Cannot find compose file:

echo   %COMPOSE_FILE%

echo Put this BAT in the repo root (folder that contains infra\).

goto END_FAIL



:FAIL_COMPOSE_UP
set "FAIL_REASON=Build failed or docker compose up failed."
set "EXIT_CODE=20"
echo ERROR: docker compose up failed.

goto END_FAIL



:FAIL_API_HEALTH
set "FAIL_REASON=API /health timeout or not reachable."
set "EXIT_CODE=30"
echo ERROR: API did not become healthy. Last logs:

docker logs --tail 200 docker-api-1

goto END_FAIL



:FAIL_KC_READY
set "FAIL_REASON=Keycloak well-known timeout or not reachable."
set "EXIT_CODE=40"
echo ERROR: Keycloak did not become ready. Last logs:

docker logs --tail 200 docker-keycloak-1

goto END_FAIL



:FAIL_TOKEN
set "FAIL_REASON=Token retrieval failed (Keycloak auth/token endpoint)."
set "EXIT_CODE=50"
echo ERROR: Could not obtain token. Last Keycloak logs:

docker logs --tail 200 docker-keycloak-1

goto END_FAIL



:FAIL_TENANTS
set "FAIL_REASON=/v1/tenants call failed (API auth/tenant pipeline)."
set "EXIT_CODE=60"
echo ERROR: /v1/tenants call failed. Last API logs:

docker logs --tail 200 docker-api-1

goto END_FAIL




:DIAG_SECTION
echo.
echo [DIAG] Capturing diagnostics snapshot...
echo.>>"%LOG_FILE%"
echo ===== DIAG %date% %time% =====>>"%LOG_FILE%"

echo --- docker version --- >>"%LOG_FILE%"
docker version >>"%LOG_FILE%" 2>&1

echo.>>"%LOG_FILE%"
echo --- docker info (selected) --- >>"%LOG_FILE%"
docker info 2>&1 | findstr /I /C:"Server Version" /C:"Operating System" /C:"OSType" /C:"Architecture" /C:"CPUs" /C:"Total Memory" /C:"Name" /C:"Docker Root Dir" >>"%LOG_FILE%"

echo.>>"%LOG_FILE%"
echo --- docker compose version --- >>"%LOG_FILE%"
docker compose version >>"%LOG_FILE%" 2>&1

echo.>>"%LOG_FILE%"
echo --- docker compose ps (current) --- >>"%LOG_FILE%"
docker compose -f "%COMPOSE_FILE%" ps >>"%LOG_FILE%" 2>&1

echo.>>"%LOG_FILE%"
echo --- port check localhost:8000 (API) --- >>"%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Test-NetConnection -ComputerName 'localhost' -Port 8000 -InformationLevel Quiet; Write-Output ('LISTENING=' + $r) } catch { Write-Output 'LISTENING=ERROR' }" >>"%LOG_FILE%" 2>&1

echo.>>"%LOG_FILE%"
echo --- port check localhost:8080 (Keycloak) --- >>"%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Test-NetConnection -ComputerName 'localhost' -Port 8080 -InformationLevel Quiet; Write-Output ('LISTENING=' + $r) } catch { Write-Output 'LISTENING=ERROR' }" >>"%LOG_FILE%" 2>&1

echo ===== END DIAG =====>>"%LOG_FILE%"
echo.
goto :eof

:END_OK
set "RESULT=OK"
set "FAIL_REASON="
set "EXIT_CODE=0"
echo.>>"%LOG_FILE%"

echo ===== OK %date% %time% =====>>"%LOG_FILE%"

echo.

echo.>>"%LOG_FILE%"
echo ===== SUMMARY =====>>"%LOG_FILE%"
echo RESULT=OK>>"%LOG_FILE%"
echo CAUSE=All checks passed.>>"%LOG_FILE%"
echo EXIT_CODE=0>>"%LOG_FILE%"
echo LOG_FILE=%LOG_FILE%>>"%LOG_FILE%"

echo.
echo ===== SUMMARY =====
echo RESULT=OK
echo CAUSE=All checks passed.
echo EXIT_CODE=0
echo LOG_FILE=%LOG_FILE%

echo.>>"%LOG_FILE%"
echo ===== SUMMARY =====>>"%LOG_FILE%"
echo RESULT=FAIL>>"%LOG_FILE%"
echo CAUSE=%FAIL_REASON%>>"%LOG_FILE%"
echo EXIT_CODE=%EXIT_CODE%>>"%LOG_FILE%"
echo LOG_FILE=%LOG_FILE%>>"%LOG_FILE%"

echo.
echo ===== SUMMARY =====
echo RESULT=FAIL
echo CAUSE=%FAIL_REASON%
echo EXIT_CODE=%EXIT_CODE%
echo LOG_FILE=%LOG_FILE%

echo --- Press any key to close ---
pause >nul

exit /b 0



:END_FAIL
if not defined EXIT_CODE set "EXIT_CODE=1"
if not defined FAIL_REASON set "FAIL_REASON=Unknown failure"
echo.>>"%LOG_FILE%"

echo ===== FAIL %date% %time% (ERRORLEVEL=%errorlevel%) =====>>"%LOG_FILE%"

echo.

echo.>>"%LOG_FILE%"
echo ===== SUMMARY =====>>"%LOG_FILE%"
echo RESULT=FAIL>>"%LOG_FILE%"
echo CAUSE=%FAIL_REASON%>>"%LOG_FILE%"
echo EXIT_CODE=%EXIT_CODE%>>"%LOG_FILE%"
echo LOG_FILE=%LOG_FILE%>>"%LOG_FILE%"

echo.
echo ===== SUMMARY =====
echo RESULT=FAIL
echo CAUSE=%FAIL_REASON%
echo EXIT_CODE=%EXIT_CODE%
echo LOG_FILE=%LOG_FILE%

echo --- Press any key to close ---

pause >nul
exit /b %EXIT_CODE%
