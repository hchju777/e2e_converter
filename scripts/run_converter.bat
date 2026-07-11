@echo off
cd /d "%~dp0.."
chcp 65001 >nul
title PsO Dashboard Converter

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py web
) else (
    echo [ERROR] Python virtual environment was not found.
    echo Please follow the installation steps in README.md first.
    pause
)
