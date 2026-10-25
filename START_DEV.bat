@echo off
setlocal
title Intrusion Monitor - React Development
cd /d "%~dp0frontend"
where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js/npm is not on PATH. Install Node.js before running Vite.
  pause
  exit /b 1
)
if not exist "node_modules\vite\bin\vite.js" (
  echo ERROR: Frontend dependencies are missing. Run npm install inside frontend.
  pause
  exit /b 1
)
echo Starting Vite for development. Keep START_ALL's backend and ML windows open.
call npm run dev
if errorlevel 1 echo ERROR: Vite stopped with an error.
pause
