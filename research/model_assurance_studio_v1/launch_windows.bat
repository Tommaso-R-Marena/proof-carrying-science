@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (echo Python 3 is required. & pause & exit /b 1)
)
if not exist ".venv\pcs_dependencies_installed.txt" (
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (echo Could not install dependencies. & pause & exit /b 1)
    echo Installed > ".venv\pcs_dependencies_installed.txt"
)
.venv\Scripts\python.exe launch.py
if errorlevel 1 pause
