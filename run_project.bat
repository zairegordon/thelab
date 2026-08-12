@echo off
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo Virtual environment not found at .venv.
    echo Creating a fresh one...
    py -3 -m venv .venv
)

if not exist "%VENV_PY%" (
    echo Failed to create .venv. Please check Python installation.
    pause
    exit /b 1
)

set "PORT=%PORT%"
if not defined PORT set "PORT=5000"

for /f %%I in ('powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue; if ($c) { ($c | Measure-Object).Count } else { 0 }" 2^>nul') do set "PORT_IN_USE=%%I"
if "%PORT_IN_USE%"=="1" (
    echo Port 5000 is in use. Switching to port 5001.
    set "PORT=5001"
)

set "FLASK_APP=app.py"
echo Starting app on http://127.0.0.1:%PORT%
"%VENV_PY%" app.py
