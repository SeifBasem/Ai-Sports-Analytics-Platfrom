@echo off
title AI Sports Analytics - Flask Server
color 0A

echo ==========================================
echo  AI Sports Analytics - Backend Server
echo ==========================================
echo.

:: Add Git to PATH for this session
set PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin

:: Navigate to script's folder
cd /d "%~dp0"

:: ── Kill any old process on port 5050 ─────────────────────────────────────
echo [*] Checking for existing processes on port 5050...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5050 " ^| findstr "LISTENING"') do (
    echo [*] Killing old process PID: %%a
    taskkill /PID %%a /F >nul 2>&1
)
echo [*] Port 5050 is clear.
echo.

:: ── Start the server ───────────────────────────────────────────────────────
echo [*] Starting Flask server...
echo [*] API will be available at http://localhost:5050
echo [*] Press CTRL+C to stop the server.
echo.
python app.py

:: If it crashes, show error and keep window open
echo.
echo [!] Server stopped. Check the error above.
pause
