@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM AviationCAMO-MRO - diagnostics helper (Windows)
REM Keeps the console open and writes logs.

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%"

call "%ROOT_DIR%start_and_test.bat"
set "RC=%ERRORLEVEL%"

echo.
echo === Diagnostics (quick) ===
echo 1) Make sure you run from the repo root OR use: start_and_test.bat
echo 2) If Docker Desktop is not running, the script will fail.
echo 3) Logs are written to: .\logs\start_and_test_*.log

echo.
if "%NO_PAUSE%"=="1" exit /b %RC%
pause
exit /b %RC%
