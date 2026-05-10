@echo off
chcp 65001 >nul
setlocal

echo.
echo   VoixClaire - creation du .exe Windows
echo   =====================================
echo.

if not exist venv (
    echo   [1/5] Creation de l'environnement Python...
    python -m venv venv
)

echo   [2/5] Installation des dependances...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt pyinstaller -q

echo   [3/5] Tests rapides...
python -m unittest discover -s tests
if %errorlevel% neq 0 (
    echo.
    echo   ERREUR: les tests ont echoue. Build annule.
    pause
    exit /b 1
)

echo   [4/5] Nettoyage ancien build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo   [5/5] Compilation PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --name "VoixClaire" ^
    --icon "voixclaire.ico" ^
    --add-data "ui;ui" ^
    --hidden-import "faster_whisper" ^
    --hidden-import "sounddevice" ^
    --hidden-import "librosa" ^
    --hidden-import "sklearn" ^
    --hidden-import "sklearn.utils._cython_blas" ^
    --hidden-import "pynput" ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --hidden-import "pyperclip" ^
    --hidden-import "scipy" ^
    --hidden-import "scipy.signal" ^
    --collect-all "faster_whisper" ^
    --collect-all "ctranslate2" ^
    main.py

echo.
echo   Termine: dist\VoixClaire.exe
echo   Au premier lancement, le modele vocal sera telecharge dans les donnees VoixClaire.
echo.
pause
