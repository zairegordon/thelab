@echo off
title The Lab - Flask Server
cd /d "%~dp0"

:: Check if Flask is already running on port 5000
netstat -ano | findstr ":5000 " > nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Flask is already running on http://127.0.0.1:5000
    start http://127.0.0.1:5000
    exit /b 0
)

echo Starting The Lab...
start "" .\.venv\Scripts\python.exe app.py

:: Wait for Flask to be ready before opening browser
:waitloop
timeout /t 1 /nobreak > nul
netstat -ano | findstr ":5000 " > nul 2>&1
if %ERRORLEVEL% neq 0 goto waitloop

start http://127.0.0.1:5000
