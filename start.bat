@echo off
REM One-command setup + run for DocBrain (Windows). See start.py.
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python start.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py start.py
    goto :eof
)

echo Python 3.11+ is required but wasn't found. Install it from https://python.org and re-run this script.
exit /b 1
