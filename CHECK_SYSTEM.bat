@echo off
setlocal
title Intrusion Monitor - Read-Only System Check
cd /d "%~dp0"
if not exist "ml\.venv\Scripts\python.exe" (
  echo ERROR: ml\.venv\Scripts\python.exe is missing.
  pause
  exit /b 1
)
"ml\.venv\Scripts\python.exe" -u "scripts\system.py" check
set "CHECK_EXIT=%ERRORLEVEL%"
if errorlevel 1 echo NOTE: One or more required services are offline or could not be checked.
pause
exit /b %CHECK_EXIT%
