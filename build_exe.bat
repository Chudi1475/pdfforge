@echo off
setlocal
title PDFForge - Build Standalone EXE
cd /d "%~dp0"

echo  Installing PyInstaller if needed...
python -m pip install --upgrade pyinstaller

echo  Building standalone exe (this can take a few minutes)...
pyinstaller --noconfirm --windowed --name PDFForge ^
    --collect-submodules pymupdf ^
    --collect-submodules PySide6 ^
    --collect-data PySide6 ^
    --hidden-import pikepdf ^
    --hidden-import PIL ^
    main.py

if errorlevel 1 (
    echo  Build failed.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Done! Find PDFForge.exe in dist\PDFForge\
echo  ============================================
echo.
pause
