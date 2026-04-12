@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║  VoixClaire - Build Portable             ║
echo   ║  Cree un dossier autonome sans install   ║
echo   ╚══════════════════════════════════════════╝
echo.

set "BUILD_DIR=%~dp0portable_build"
set "OUT_DIR=%~dp0VoixClaire_Portable"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_ZIP=python-3.11.9-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/%PYTHON_ZIP%"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

:: Nettoyage
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%BUILD_DIR%"
mkdir "%OUT_DIR%"

:: ===== 1. Telecharger Python Embedded =====
echo   [1/6] Telechargement de Python embarque...
curl -L -o "%BUILD_DIR%\%PYTHON_ZIP%" "%PYTHON_URL%"
if %errorlevel% neq 0 (
    echo   [!] Echec telechargement Python. Verifiez votre connexion.
    pause
    exit /b 1
)

:: Extraire Python
echo   [2/6] Extraction de Python...
mkdir "%OUT_DIR%\python"
tar -xf "%BUILD_DIR%\%PYTHON_ZIP%" -C "%OUT_DIR%\python"

:: Activer les imports de site-packages
:: (par defaut, Python embedded desactive import site)
set "PTH_FILE="
for %%f in ("%OUT_DIR%\python\python*._pth") do set "PTH_FILE=%%f"
if defined PTH_FILE (
    echo import site>> "!PTH_FILE!"
)

:: ===== 2. Installer pip =====
echo   [3/6] Installation de pip...
curl -L -o "%BUILD_DIR%\get-pip.py" "%GET_PIP_URL%"
"%OUT_DIR%\python\python.exe" "%BUILD_DIR%\get-pip.py" --no-warn-script-location -q

:: ===== 3. Installer les dependances =====
echo   [4/6] Installation des dependances (peut prendre plusieurs minutes)...
"%OUT_DIR%\python\python.exe" -m pip install --no-warn-script-location -q ^
    faster-whisper ^
    PyQt6 ^
    sounddevice ^
    numpy ^
    scipy ^
    librosa ^
    scikit-learn ^
    pynput ^
    pyperclip

:: ===== 4. Copier le code source =====
echo   [5/6] Copie de VoixClaire...
mkdir "%OUT_DIR%\app"
mkdir "%OUT_DIR%\app\ui"

copy "%~dp0main.py" "%OUT_DIR%\app\" >nul
copy "%~dp0config.py" "%OUT_DIR%\app\" >nul
copy "%~dp0database.py" "%OUT_DIR%\app\" >nul
copy "%~dp0audio_engine.py" "%OUT_DIR%\app\" >nul
copy "%~dp0transcriber.py" "%OUT_DIR%\app\" >nul
copy "%~dp0adaptive_learner.py" "%OUT_DIR%\app\" >nul
copy "%~dp0text_injector.py" "%OUT_DIR%\app\" >nul
copy "%~dp0sync.py" "%OUT_DIR%\app\" >nul
copy "%~dp0ui\*.py" "%OUT_DIR%\app\ui\" >nul

:: ===== 5. Creer le lanceur =====
echo   [6/6] Creation du lanceur...

:: Lanceur principal (double-clic pour demarrer)
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo start "" "python\pythonw.exe" "app\main.py"
) > "%OUT_DIR%\VoixClaire.bat"

:: Lanceur avec console (pour debug)
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo "python\python.exe" "app\main.py"
echo pause
) > "%OUT_DIR%\VoixClaire_debug.bat"

:: Pre-telecharger le modele Whisper
echo.
echo   Telechargement du modele de reconnaissance vocale (~500Mo)...
echo   (premiere utilisation sera instantanee grace a ca)
"%OUT_DIR%\python\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('   Modele telecharge !')"

:: Nettoyage
rmdir /s /q "%BUILD_DIR%" 2>nul

:: Calculer la taille
set size=0
for /f "tokens=3" %%a in ('dir /s "%OUT_DIR%" ^| findstr "File(s)"') do set size=%%a

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║           Build termine !                ║
echo   ╠══════════════════════════════════════════╣
echo   ║                                          ║
echo   ║  Le dossier "VoixClaire_Portable" est    ║
echo   ║  pret a etre copie sur une cle USB       ║
echo   ║  ou un partage reseau.                   ║
echo   ║                                          ║
echo   ║  Pour lancer : double-clic sur           ║
echo   ║  VoixClaire.bat                          ║
echo   ║                                          ║
echo   ║  Aucune installation requise !           ║
echo   ║  Aucun droit administrateur !            ║
echo   ║                                          ║
echo   ╚══════════════════════════════════════════╝
echo.
pause
