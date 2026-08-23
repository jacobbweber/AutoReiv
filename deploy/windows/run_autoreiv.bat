@echo off
REM AutoReiv Windows Batch Launcher
REM [REQ-DEPLOY-004]

setlocal enabledelayedexpansion
title AutoReiv Control Plane

cd /d "%~dp0\..\.."

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo ============================================================
echo   Starting AutoReiv Control Plane on Windows
echo ============================================================

python -m src.cli.main serve --host 0.0.0.0 --port 8000

pause
