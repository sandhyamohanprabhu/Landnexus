@echo off
title LANDNEXUS Cloudflare Tunnel :8001
echo.
echo  ==========================================
echo   LANDNEXUS  -  Cloudflare Tunnel Launcher
echo  ==========================================
echo   Target : http://127.0.0.1:8001
echo  ==========================================
echo.
cd /d "%~dp0"
if not exist "cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found in %CD%
    pause
    exit /b 1
)
cloudflared.exe tunnel --url http://127.0.0.1:8001
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cloudflare tunnel stopped or failed.
    pause
)
