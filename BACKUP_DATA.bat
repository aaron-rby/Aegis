@echo off
setlocal
title Intrusion Monitor - Backup Camera Data
cd /d "%~dp0"
if not exist "ml\.venv\Scripts\python.exe" (
  echo ERROR: ml\.venv\Scripts\python.exe is missing.
  pause
  exit /b 1
)
"ml\.venv\Scripts\python.exe" -u "scripts\system.py" backup
if errorlevel 1 (
  echo Backup incomplete. Check the error above; do not treat a folder without manifest.json as complete.
  pause
  exit /b 1
)
pause
