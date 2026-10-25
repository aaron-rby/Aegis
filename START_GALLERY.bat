@echo off
setlocal
title ESP32 Camera Gallery
set "GALLERY_DIR=C:\Users\aaron\Documents\Intruder Detection System Project\local-photo-gallery"
if not exist "%GALLERY_DIR%\server.py" (
  echo ERROR: Gallery server was not found at:
  echo %GALLERY_DIR%\server.py
  pause
  exit /b 1
)
cd /d "%GALLERY_DIR%"
python server.py
pause
