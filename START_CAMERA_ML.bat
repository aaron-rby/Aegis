@echo off
setlocal
title ESP32 Camera - Reliable ML Worker
cd /d "%~dp0"
if not exist "ml\.venv\Scripts\python.exe" (
  echo ERROR: The ML Python environment is missing at ml\.venv\Scripts\python.exe
  pause
  exit /b 1
)
if not exist "backend\config.local.json" (
  echo ERROR: backend\config.local.json is missing.
  pause
  exit /b 1
)
"ml\.venv\Scripts\python.exe" -u "backend\worker.py"
if errorlevel 1 (
  echo ML worker stopped with an error. Read the message above.
  pause
  exit /b 1
)
pause
