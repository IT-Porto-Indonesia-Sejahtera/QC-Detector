@echo off
REM Move to the directory of the script
cd /d "%~dp0"

REM Use Python inside the virtual environment
.\venv\Scripts\python.exe main.py

pause
