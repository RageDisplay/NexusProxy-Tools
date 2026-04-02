@echo off
REM Launch Amnezia Proxy Setup

echo.
echo Starting Amnezia Proxy Setup...
echo.

python amnezia_proxy_setup.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Make sure Python is installed and dependencies are installed.
    echo Run: install_requirements.bat
    echo.
    pause
)
