@echo off
setlocal
title Intruder Camera - Phase 2 Backend
cd /d "%~dp0.."
if not exist "backend\config.local.json" (
  echo ERROR: Copy backend\config.example.json to backend\config.local.json and set the existing paths.
  pause
  exit /b 1
)
python backend\server.py
if errorlevel 1 (
  echo Backend stopped with an error. Check the message above.
  pause
  exit /b 1
)
pause
