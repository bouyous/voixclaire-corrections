@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo VoixClaire n'est pas installe.
    echo Lance "install.bat" d'abord !
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
start "" pythonw main.py
