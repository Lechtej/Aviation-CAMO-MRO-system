@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM AviationCAMO-MRO - start + basic health checks (Windows)
REM - No external deps (no 'tee' required)
REM - Safe for double-click (keeps window open on errors)

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%"
set "LOGS_DIR=%ROOT_DIR%logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%" >nul 2>&1

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOG_FILE=%LOGS_DIR%\start_and_test_%TS%.log"

call :log "=== AviationCAMO-MRO start_and_test (v0.2.42) ==="
call :log "Root: %ROOT_DIR%"
call :log "Log:  %LOG_FILE%"

where docker >nul 2>&1 || (call :log "ERROR: Docker not found in PATH." & goto :fail)
docker info >nul 2>&1 || (call :log "ERROR: Docker engine not running." & goto :fail)

pushd "%ROOT_DIR%" || (call :log "ERROR: Cannot cd to root." & goto :fail)
set "COMPOSE_FILE=infra\docker\docker-compose.yml"
if not exist "%COMPOSE_FILE%" (call :log "ERROR: Compose file not found: %COMPOSE_FILE%" & popd & goto :fail)

call :log "Running: docker compose -f %COMPOSE_FILE% up -d --build"
docker compose -f "%COMPOSE_FILE%" up -d --build >>"%LOG_FILE%" 2>&1
if errorlevel 1 (call :log "ERROR: docker compose up failed. Check log." & popd & goto :fail)

call :log "Running: docker compose -f %COMPOSE_FILE% ps"
docker compose -f "%COMPOSE_FILE%" ps >>"%LOG_FILE%" 2>&1

call :log "Healthcheck API: http://localhost:8000/docs"
set "HC_URL=http://localhost:8000/docs"
set "HC_MAX=30"
set "HC_OK=0"
for /L %%A in (1,1,%HC_MAX%) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri \"%HC_URL%\" -UseBasicParsing -TimeoutSec 10; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
  if !errorlevel! EQU 0 (
    set "HC_OK=1"
    goto :hc_done
  )
  timeout /t 1 >nul
)
:hc_done
if "%HC_OK%" NEQ "1" (call :log "ERROR: API /docs not reachable (HTTP 200 expected)." & popd & goto :fail)
call :log "OK: API is up (HTTP 200)."

call :log "Healthcheck UI: http://localhost:3000"
set "UI_URL=http://localhost:3000"
set "UI_MAX=30"
set "UI_OK=0"
for /L %%A in (1,1,%UI_MAX%) do (
  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri \"%UI_URL%\" -UseBasicParsing -TimeoutSec 10; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
  if !errorlevel! EQU 0 (
    set "UI_OK=1"
    goto :ui_done
  )
  timeout /t 1 >nul
)
:ui_done
if "%UI_OK%" NEQ "1" (call :log "ERROR: UI not reachable (HTTP 200 expected)." & popd & goto :fail)
call :log "OK: UI is up (HTTP 200)."
popd

call :log "Done."
goto :success

:log
set "MSG=%~1"
echo %MSG%
echo %MSG%>>"%LOG_FILE%"
exit /b 0

:fail
call :log "FAILED."
if not "%NO_PAUSE%"=="1" pause
exit /b 1

:success
if not "%NO_PAUSE%"=="1" pause
exit /b 0
