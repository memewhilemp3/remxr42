@echo off
setlocal enabledelayedexpansion
title remxr42 - Dual Circular Polar Vinyl Workstation

echo ============================================================
echo   remxr42 // DUAL CIRCULAR POLAR VINYL WORKSTATION
echo ============================================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Python is not detected on your PATH.
    echo [*] Opening Zero-Install Standalone Web Edition instead...
    if exist "remxr42.html" (
        start "" "remxr42.html"
    ) else (
        echo [!] remxr42.html not found in current directory.
    )
    pause
    exit /b 0
)

REM Setup local virtual environment if not already present
if not exist ".venv" (
    echo [*] Creating isolated virtual environment in .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo [*] Installing dependencies (Streamlit, NumPy, SciPy, SoundFile, Pillow)...
    pip install --quiet -e .
) else (
    call .venv\Scripts\activate.bat
)

echo [*] Starting remxr42 on http://localhost:8542 ...
remxr42 --port 8542

pause
