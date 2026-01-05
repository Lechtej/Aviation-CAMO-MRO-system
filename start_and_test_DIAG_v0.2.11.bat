@echo off
setlocal
set "DIAG=1"
call "%~dp0start_and_test_v0.2.11.bat"
exit /b %errorlevel%
