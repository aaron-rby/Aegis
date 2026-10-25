@echo off
setlocal
title Intrusion Monitor - React Gallery Backend
cd /d "%~dp0"
if not exist "backend\config.local.json" (
  echo ERROR: backend\config.local.json is missing.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo ERROR: React build is missing. Run npm install and npm run build in frontend.
  pause
  exit /b 1
)
python -u "backend\server.py"
if errorlevel 1 (
  echo Backend stopped with an error. Check the message above.
  pause
  exit /b 1
)
pause
