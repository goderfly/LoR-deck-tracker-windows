@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Legends of Runeterra Deck Tracker - Build Pipeline
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

python scripts\build_exe.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b 1
)

echo.
echo Build finished successfully! The executable is located at:
echo release\LoRDeckTracker.exe
echo.
pause
