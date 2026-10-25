@echo off
chcp 65001 >nul
setlocal
title Sentinel — Hardware Monitor
cd /d "%~dp0"
echo Sentinel Hardware Monitor
echo.
if not exist "website\app.py" (
  echo ERROR: website\app.py was not found. Keep START_HARDWARE.bat in the main project folder.
  pause
  exit /b 1
)
if not exist "website\.venv\Scripts\python.exe" (
  echo ERROR: The Sentinel Python environment was not found at website\.venv\Scripts\python.exe.
  echo See website\README.md for environment setup. Existing launchers have not been changed.
  pause
  exit /b 1
)
"website\.venv\Scripts\python.exe" "website\hardware_launcher.py" %*
if errorlevel 1 (
  echo.
  echo Startup failed. Review the error above and website\data\hardware-service.log.
  pause
  exit /b 1
)
echo.
echo Service ready. The service keeps running when this launcher finishes.
endlocal
