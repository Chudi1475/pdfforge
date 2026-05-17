@echo off
setlocal
title PDFForge - First-Time Setup

echo.
echo  ============================================
echo   PDFForge installer
echo  ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  Python is not installed or not on PATH.
    echo  Please install Python 3.10+ from https://python.org
    echo  Be sure to tick "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo  Installing dependencies, this only happens once...
echo.
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo  Install failed. Try running this file as Administrator.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Done! Double-click run.bat to start PDFForge.
echo  ============================================
echo.
pause
