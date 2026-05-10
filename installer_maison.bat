@echo off
setlocal enabledelayedexpansion

echo.
echo   VoixClaire - Installation Maison
echo   =================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\VoixClaire"
set "APP_DIR=%INSTALL_DIR%\app"
set "TEMP_DIR=%TEMP%\voixclaire_install"

if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"
mkdir "%INSTALL_DIR%" 2>nul
mkdir "%APP_DIR%" 2>nul
mkdir "%APP_DIR%\ui" 2>nul

REM === 1. Python ===
if exist "%INSTALL_DIR%\python\python.exe" (
    echo   [1/6] Python deja present.
) else (
    echo   [1/6] Telechargement de Python...
    curl -L -s -o "%TEMP_DIR%\python.zip" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    if !errorlevel! neq 0 (
        echo   ERREUR: Pas de connexion internet.
        pause
        exit /b 1
    )
    mkdir "%INSTALL_DIR%\python"
    tar -xf "%TEMP_DIR%\python.zip" -C "%INSTALL_DIR%\python"
    for %%f in ("%INSTALL_DIR%\python\python*._pth") do (
        echo import site>> "%%f"
    )
)

REM === 2. Pip ===
if exist "%INSTALL_DIR%\python\Scripts\pip.exe" (
    echo   [2/6] pip deja present.
) else (
    echo   [2/6] Installation de pip...
    curl -L -s -o "%TEMP_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py"
    "%INSTALL_DIR%\python\python.exe" "%TEMP_DIR%\get-pip.py" --no-warn-script-location -q 2>nul
)

REM === 3. Dependances ===
echo   [3/6] Installation des dependances...
echo         (peut prendre quelques minutes)
"%INSTALL_DIR%\python\python.exe" -m pip install --no-warn-script-location -q faster-whisper PyQt6 sounddevice numpy scipy librosa scikit-learn pynput pyperclip 2>nul

REM === 4. Code ===
echo   [4/6] Copie de VoixClaire...
for %%f in (main.py config.py database.py audio_engine.py transcriber.py adaptive_learner.py text_injector.py sync.py) do (
    copy /y "%~dp0%%f" "%APP_DIR%\" >nul
)
copy /y "%~dp0ui\*.py" "%APP_DIR%\ui\" >nul
copy /y "%~dp0voixclaire.ico" "%INSTALL_DIR%\" >nul 2>nul

REM === 5. Modele ===
echo   [5/6] Telechargement du modele vocal (~500Mo)...
"%INSTALL_DIR%\python\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8'); print('         OK !')"

REM === 6. Raccourcis ===
echo   [6/6] Creation des raccourcis...

REM Lanceur VBS invisible
(
echo Set oShell = CreateObject("WScript.Shell"^)
echo oShell.CurrentDirectory = "%INSTALL_DIR%"
echo oShell.Run """" ^& "%INSTALL_DIR%\python\pythonw.exe" ^& """ """ ^& "%APP_DIR%\main.py" ^& """", 0, False
) > "%INSTALL_DIR%\VoixClaire.vbs"

REM Raccourci Bureau
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'VoixClaire.lnk')); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%INSTALL_DIR%\VoixClaire.vbs\"'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'VoixClaire'; $s.IconLocation = '%INSTALL_DIR%\voixclaire.ico,0'; $s.Save()" 2>nul

REM Raccourci Menu Demarrer
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU%\VoixClaire.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%INSTALL_DIR%\VoixClaire.vbs\"'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'VoixClaire'; $s.IconLocation = '%INSTALL_DIR%\voixclaire.ico,0'; $s.Save()" 2>nul

REM Nettoyage
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo   =================================
echo   Installation terminee !
echo.
echo   Raccourci "VoixClaire" cree sur :
echo     - Le Bureau
echo     - Le Menu Demarrer
echo.
echo   Clic droit sur le raccourci du
echo   Menu Demarrer pour l'epingler
echo   a la barre des taches.
echo   =================================
echo.

set /p LAUNCH="  Lancer maintenant ? (O/N) : "
if /i "%LAUNCH%"=="O" (
    start "" wscript.exe "%INSTALL_DIR%\VoixClaire.vbs"
)

pause
