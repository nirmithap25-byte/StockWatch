@echo off
title "StockWatch Setup & Startup Tool"
cd /d "%~dp0"

if not exist "backend\venv" (
    echo ===================================================
    echo  StockWatch: Setting up virtual environment...
    echo ===================================================
    echo.
    python -m venv backend\venv
    if errorlevel 1 (
        echo Error: Python is not installed or not added to PATH!
        echo Please install Python 3 and make sure to check "Add Python to PATH".
        pause
        exit /b
    )
    echo.
    echo Installing dependencies from requirements.txt...
    backend\venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies!
        pause
        exit /b
    )
    echo.
    echo Setup completed successfully!
    echo ===================================================
    echo.
)

echo Starting StockWatch Flask Server...
cd backend
venv\Scripts\python app.py
pause
