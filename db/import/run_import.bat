@echo off
setlocal enabledelayedexpansion

echo === AviationCAMO-MRO PGL Fleet Import (v0.2.3) ===

REM Assumes you run this from repo root on Windows.

set XLSX=db\import\source\Floty_MRO_PGL_v1.1.1_FINAL.xlsx
set OUT=db\import\export

if not exist "%XLSX%" (
  echo [ERROR] Missing XLSX: %XLSX%
  exit /b 1
)

echo [1/4] Exporting CSVs from XLSX...
python db\import\scripts\import_pgl_fleet.py --xlsx "%XLSX%" --out "%OUT%"
if errorlevel 1 (
  echo [ERROR] CSV export failed.
  exit /b 1
)

echo.
echo [2/4] Applying migrations + seed...
echo Provide Postgres connection info:
set /p PGHOST=PGHOST (default: localhost):
if "%PGHOST%"=="" set PGHOST=localhost
set /p PGPORT=PGPORT (default: 5432):
if "%PGPORT%"=="" set PGPORT=5432
set /p PGUSER=PGUSER (default: aviation):
if "%PGUSER%"=="" set PGUSER=aviation
set /p PGDATABASE=PGDATABASE (default: aviation):
if "%PGDATABASE%"=="" set PGDATABASE=aviation

set PGPASSWORD=
set /p PGPASSWORD=PGPASSWORD (will not be hidden):

echo Running migrations...
psql -v ON_ERROR_STOP=1 -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f db\migrations\public\0001_public_core.sql
if errorlevel 1 exit /b 1
psql -v ON_ERROR_STOP=1 -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f db\migrations\public\0002_public_aircraft_registration_history.sql
if errorlevel 1 exit /b 1

echo Seeding PGL core tenants...
psql -v ON_ERROR_STOP=1 -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f db\seed\seed_public_pgl_core_v0.2.3.sql
if errorlevel 1 exit /b 1

echo.
echo [3/4] Loading CSVs into DB...
psql -v ON_ERROR_STOP=1 -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c "\set csvdir 'db/import/export'" -f db\import\staging\load_from_csv.sql
if errorlevel 1 exit /b 1

echo.
echo [4/4] Verification...
psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f db\import\scripts\verify_import.sql

echo.
echo DONE.
endlocal
