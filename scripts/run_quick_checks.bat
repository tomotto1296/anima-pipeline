@echo off
setlocal
cd /d "%~dp0\.."
python scripts\run_quick_checks.py %*
exit /b %errorlevel%
