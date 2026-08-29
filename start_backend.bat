@echo off
title ANVAYA Backend Engine [Port 8080]
color 0A

echo ===============================================================================
echo     ANVAYA FastAPI Backend Engine (Port 8080)
echo ===============================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [*] Starting Uvicorn FastAPI Server on http://0.0.0.0:8080 ...
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] FastAPI Backend server stopped.
    pause
)
