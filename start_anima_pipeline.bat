@echo off
cd /d "%~dp0"
echo ==============================
echo  Anima Pipeline Launcher
echo ==============================

if exist ".\python_embeded\python.exe" (
    set PYTHON=.\python_embeded\python.exe
    echo [INFO] Using bundled Python: %PYTHON%
) else (
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
)

"%PYTHON%" -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requests...
    "%PYTHON%" -m pip install requests
    if errorlevel 1 (
        echo [ERROR] Failed to install requests.
        echo Please run manually: pip install requests
        pause
        exit /b 1
    )
)

echo [INFO] Starting server... Open http://localhost:7860
echo.
"%PYTHON%" anima_pipeline.py
pause
