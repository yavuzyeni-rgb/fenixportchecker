@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 bulunamadi. https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m portgozu
if errorlevel 1 pause
