@echo off
cd /d "%~dp0.."
chcp 65001 >nul
title Build PsO Dashboard Converter
set /p APP_VERSION=<config\VERSION

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller was not found.
    echo Run: .venv\Scripts\python.exe -m pip install -r requirements/dev.txt
    pause
    exit /b 1
)

".venv\Scripts\pyinstaller.exe" --noconfirm --clean --distpath release --workpath build scripts\PsO_Dashboard_Converter.spec
if errorlevel 1 (
    echo [ERROR] EXE build failed.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] release\PsO_Dashboard_Converter_v%APP_VERSION%.exe
pause
