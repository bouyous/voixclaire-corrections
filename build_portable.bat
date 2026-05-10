@echo off
setlocal enabledelayedexpansion

echo.
echo   VoixClaire - Build Portable (cle USB)
echo   ======================================
echo.

set "BUILD_DIR=%~dp0_temp_build"
set "OUT_DIR=%~dp0VoixClaire_Portable"
set "PYTHON_ZIP=python-3.11.9-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/%PYTHON_ZIP%"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%BUILD_DIR%"
mkdir "%OUT_DIR%"
mkdir "%OUT_DIR%\python"
mkdir "%OUT_DIR%\app"
mkdir "%OUT_DIR%\app\ui"
mkdir "%OUT_DIR%\data"

echo   [1/7] Telechargement de Python 3.11...
curl -L -s -o "%BUILD_DIR%\%PYTHON_ZIP%" "%PYTHON_URL%"
if !errorlevel! neq 0 (
    echo   ERREUR: Impossible de telecharger Python. Verifiez internet.
    pause
    exit /b 1
)

echo   [2/7] Extraction de Python...
tar -xf "%BUILD_DIR%\%PYTHON_ZIP%" -C "%OUT_DIR%\python"

REM Activer site-packages dans python embedded
for %%f in ("%OUT_DIR%\python\python*._pth") do (
    echo import site>> "%%f"
)

echo   [3/7] Installation de pip...
curl -L -s -o "%BUILD_DIR%\get-pip.py" "%GET_PIP_URL%"
"%OUT_DIR%\python\python.exe" "%BUILD_DIR%\get-pip.py" --no-warn-script-location -q 2>nul

echo   [4/7] Installation des dependances...
echo         (cela peut prendre plusieurs minutes)
"%OUT_DIR%\python\python.exe" -m pip install --no-warn-script-location -q faster-whisper PyQt6 sounddevice numpy scipy librosa scikit-learn pynput pyperclip 2>nul

echo   [5/7] Copie de VoixClaire...
for %%f in (main.py config.py database.py audio_engine.py transcriber.py adaptive_learner.py text_injector.py sync.py verifier_integrite.py) do (
    copy /y "%~dp0%%f" "%OUT_DIR%\app\" >nul
)
copy /y "%~dp0ui\*.py" "%OUT_DIR%\app\ui\" >nul
copy /y "%~dp0voixclaire.ico" "%OUT_DIR%\" >nul 2>nul

echo   [6/7] Telechargement du modele vocal (~1.5Go)...
"%OUT_DIR%\python\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8'); print('         OK !')"

echo   [7/7] Mise en forme du dossier...

REM Tout le technique va dans un sous-dossier cache "_engine"
mkdir "%OUT_DIR%\_engine"
move "%OUT_DIR%\python" "%OUT_DIR%\_engine\python" >nul
move "%OUT_DIR%\app" "%OUT_DIR%\_engine\app" >nul
move "%OUT_DIR%\data" "%OUT_DIR%\_engine\data" >nul
attrib +h "%OUT_DIR%\_engine"

REM Lanceur VBS invisible (cache)
(
echo Set oShell = CreateObject("WScript.Shell"^)
echo sDir = CreateObject("Scripting.FileSystemObject"^).GetParentFolderName(WScript.ScriptFullName^)
echo oShell.CurrentDirectory = sDir
echo oShell.Run "_engine\python\pythonw.exe _engine\app\main.py", 0, False
) > "%OUT_DIR%\_lancer.vbs"
attrib +h "%OUT_DIR%\_lancer.vbs"

REM Le seul fichier visible : le raccourci avec icone
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%OUT_DIR%\VoixClaire.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%OUT_DIR%\_lancer.vbs\"'; $s.WorkingDirectory = '%OUT_DIR%'; $s.Description = 'VoixClaire - Clique pour dicter'; $s.IconLocation = '%OUT_DIR%\voixclaire.ico,0'; $s.Save()" 2>nul

REM Fallback .bat (cache sauf si le .lnk echoue)
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" "_engine\python\pythonw.exe" "_engine\app\main.py"
) > "%OUT_DIR%\VoixClaire.bat"

REM Debug cache
(
echo @echo off
echo cd /d "%%~dp0"
echo "_engine\python\python.exe" "_engine\app\main.py"
echo pause
) > "%OUT_DIR%\_debug.bat"
attrib +h "%OUT_DIR%\_debug.bat"

REM Cacher l'icone (utilisee par le raccourci mais pas besoin de la voir)
attrib +h "%OUT_DIR%\voixclaire.ico"

REM Signature d'integrite
"%OUT_DIR%\_engine\python\python.exe" "%OUT_DIR%\_engine\app\verifier_integrite.py" --generate "%OUT_DIR%\_engine\app" 2>nul

REM Nettoyage
rmdir /s /q "%BUILD_DIR%" 2>nul

echo.
echo   ======================================
echo   Build termine !
echo.
echo   Le dossier "VoixClaire_Portable"
echo   ne contient qu'un seul fichier :
echo.
echo       VoixClaire  (raccourci avec icone)
echo.
echo   Copie ce dossier sur la cle USB.
echo   ======================================
echo.
pause
