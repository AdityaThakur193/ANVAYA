@echo off
title Stop ANVAYA Servers
color 0C

echo ===============================================================================
echo     Stopping ANVAYA Servers (Ports 8080 and 3000)
echo ===============================================================================
echo.

echo [*] Terminating processes on Port 8080 (FastAPI Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8080" ^| findstr "LISTENING"') do (
    echo     - Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Terminating processes on Port 3000 (Vite Frontend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo     - Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [*] All ANVAYA server processes on ports 8080 and 3000 stopped.
echo.
pause
