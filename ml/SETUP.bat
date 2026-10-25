@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe python -m venv venv
if exist requirements-lock.txt (
  venv\Scripts\python.exe -m pip install -r requirements-lock.txt
) else (
  venv\Scripts\python.exe -m pip install -r requirements.txt
)
if errorlevel 1 exit /b 1
venv\Scripts\python.exe -m pip freeze > requirements-lock.txt
