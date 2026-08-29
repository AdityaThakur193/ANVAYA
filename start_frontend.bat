@echo off
title ANVAYA Frontend UI [Port 3000]
color 0E

echo ===============================================================================
echo     ANVAYA Vite React Frontend UI (Port 3000)
echo ===============================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%frontend"

if not exist "node_modules" (
    echo [*] Installing frontend npm packages...
    call npm.cmd install
)

echo [*] Starting Vite React Development Server...
call npm.cmd run dev

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] Vite server stopped.
    pause
)
