@echo off
setlocal
title Aegis - Hardware Monitor and ML
cd /d "%~dp0"
if not exist "ml\.venv\Scripts\python.exe" (
  echo ERROR: ml\.venv\Scripts\python.exe is missing. Recreate the Python environment first.
  pause
  exit /b 1
)
"ml\.venv\Scripts\python.exe" -u "scripts\system.py" start
set "AEGIS_START_EXIT=%ERRORLEVEL%"
if not "%AEGIS_START_EXIT%"=="0" goto startup_failed

echo Startup complete. Backend and ML are ready.
echo Hardware dashboard: http://localhost:5000/#hardware
echo No USB port is opened until you select Connect USB in the dashboard.
pause
exit /b 0

:startup_failed
if "%AEGIS_START_EXIT%"=="130" (
  echo Startup cancelled. Existing backend and ML services were left running.
) else (
  echo Startup failed or was interrupted. Exit code: %AEGIS_START_EXIT%
  echo Read the error above and leave any existing backend/ML windows open.
)
pause
exit /b %AEGIS_START_EXIT%
