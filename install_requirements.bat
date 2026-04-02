@echo off
REM Install Python dependencies for NexusProxy - Tools Amnezia WG

echo.
echo Installing required Python packages...
echo.

python -m pip install --upgrade pip
python -m pip install paramiko

echo.
echo Installation complete!
echo.
pause
