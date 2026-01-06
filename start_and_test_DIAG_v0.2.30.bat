@echo off
REM ============================================================
REM AviationCAMO-MRO - Start + quick diagnostics (v0.2.30)
REM ============================================================
call "%~dp0start_and_test_v0.2.30.bat"
echo.
echo === DIAG: docker compose ps ===
docker compose -f "infra\docker\docker-compose.yml" ps
echo.
echo === DIAG: last 80 lines of api logs ===
docker compose -f "infra\docker\docker-compose.yml" logs --tail=80 api
echo.
exit /b 0
