@echo off
setlocal
cd /d "%~dp0"
title Aegis - Camera Dataset Labeling
"ml\.venv\Scripts\python.exe" -u "ml\camera_labeler.py"
if errorlevel 1 pause
