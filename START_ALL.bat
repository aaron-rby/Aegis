@echo off
setlocal
title Sentinel AI - Hardware Monitor and ML
cd /d "%~dp0"
if not exist "ml\.venv\Scripts\python.exe" (
  echo ERROR: ml\.venv\Scripts\python.exe is missing. Recreate the Python environment first.
  pause
  exit /b 1
)
"ml\.venv\Scripts\python.exe" -u "scripts\system.py" start
if errorlevel 1 (
  echo Startup failed. Read the error above and leave any existing backend/ML windows open.
  pause
  exit /b 1
)
echo Startup complete. Backend and ML each have their own console window.
echo Hardware dashboard: http://localhost:5000/#hardware
echo No USB port is opened until you select Connect USB in the dashboard.
pause
