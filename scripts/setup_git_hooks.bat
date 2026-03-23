@echo off
setlocal
cd /d "%~dp0\.."
powershell -ExecutionPolicy Bypass -File scripts\setup_git_hooks.ps1 %*
exit /b %errorlevel%
