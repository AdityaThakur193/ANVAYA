@echo off
setlocal
title ANVAYA Launcher
color 0B

echo ===============================================================================
echo     ANVAYA -- Multimodal Offline Air-Gapped Intelligence Platform
echo     Smart India Hackathon - NTRO (Prime Minister's Office)
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [*] Starting ANVAYA FastAPI Backend Engine on Port 8080...
start "ANVAYA Backend" start_backend.bat

echo [*] Starting ANVAYA React Frontend UI on Port 3000...
start "ANVAYA Frontend" start_frontend.bat

echo [*] Waiting for web application to initialize...
ping -n 5 127.0.0.1 >nul 2>&1

echo [*] Opening ANVAYA Intelligence Console in default browser...
start "" "http://localhost:3000"

echo.
echo ===============================================================================
echo  ANVAYA IS RUNNING LOCALLY
echo ===============================================================================
echo   - Frontend Web UI :  http://localhost:3000
echo   - Backend REST API:  http://localhost:8080
echo   - API Health Check:  http://localhost:8080/api/health/full
echo ===============================================================================
echo  Both server windows (Backend and Frontend) are now running.
echo  To stop all servers, run stop_anvaya.bat or close the server windows.
echo ===============================================================================
echo.
pause
