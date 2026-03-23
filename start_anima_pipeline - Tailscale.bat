@echo off
cd /d "%~dp0"
echo ==============================
echo  Anima Pipeline Launcher
echo ==============================

python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found.
        echo Please install Python 3.10 or later.
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requests...
    %PYTHON% -m pip install requests
    if errorlevel 1 (
        echo [ERROR] Failed to install requests.
        echo Please run manually: pip install requests
        pause
        exit /b 1
    )
)

set TS_IP=
for /f "usebackq delims=" %%i in (`tailscale ip -4 2^>nul`) do (
    if not defined TS_IP set TS_IP=%%i
)

if defined TS_IP (
    echo [INFO] Starting server... Open http://%TS_IP%:7860
) else (
    echo [WARN] Tailscale IP not found. Is Tailscale connected?
    echo [INFO] Starting server... Open http://localhost:7860
)

echo.
%PYTHON% anima_pipeline.py
pause
