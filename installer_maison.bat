@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║   VoixClaire - Installation Maison       ║
echo   ║   Un clic et ca marche !                 ║
echo   ╚══════════════════════════════════════════╝
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\VoixClaire"
set "APP_DIR=%INSTALL_DIR%\app"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_ZIP=python-3.11.9-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/%PYTHON_ZIP%"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "TEMP_DIR=%TEMP%\voixclaire_install"

:: Nettoyage temp
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

:: Creer le dossier d'installation
mkdir "%INSTALL_DIR%" 2>nul
mkdir "%APP_DIR%" 2>nul
mkdir "%APP_DIR%\ui" 2>nul

:: ===== 1. Python Embedded =====
if exist "%INSTALL_DIR%\python\python.exe" (
    echo   [1/6] Python deja installe, on passe.
) else (
    echo   [1/6] Telechargement de Python...
    curl -L -o "%TEMP_DIR%\%PYTHON_ZIP%" "%PYTHON_URL%"
    if !errorlevel! neq 0 (
        echo   [!] Echec telechargement. Verifiez votre connexion internet.
        pause
        exit /b 1
    )
    echo   [1/6] Extraction de Python...
    mkdir "%INSTALL_DIR%\python"
    tar -xf "%TEMP_DIR%\%PYTHON_ZIP%" -C "%INSTALL_DIR%\python"

    :: Activer site-packages
    for %%f in ("%INSTALL_DIR%\python\python*._pth") do (
        echo import site>> "%%f"
    )
)

:: ===== 2. Pip =====
if exist "%INSTALL_DIR%\python\Scripts\pip.exe" (
    echo   [2/6] pip deja installe, on passe.
) else (
    echo   [2/6] Installation de pip...
    curl -L -o "%TEMP_DIR%\get-pip.py" "%GET_PIP_URL%"
    "%INSTALL_DIR%\python\python.exe" "%TEMP_DIR%\get-pip.py" --no-warn-script-location -q
)

:: ===== 3. Dependances =====
echo   [3/6] Installation des dependances...
echo         (peut prendre plusieurs minutes la premiere fois)
"%INSTALL_DIR%\python\python.exe" -m pip install --no-warn-script-location -q ^
    faster-whisper ^
    PyQt6 ^
    sounddevice ^
    numpy ^
    scipy ^
    librosa ^
    scikit-learn ^
    pynput ^
    pyperclip

:: ===== 4. Copier le code =====
echo   [4/6] Copie de VoixClaire...
copy /y "%~dp0main.py" "%APP_DIR%\" >nul
copy /y "%~dp0config.py" "%APP_DIR%\" >nul
copy /y "%~dp0database.py" "%APP_DIR%\" >nul
copy /y "%~dp0audio_engine.py" "%APP_DIR%\" >nul
copy /y "%~dp0transcriber.py" "%APP_DIR%\" >nul
copy /y "%~dp0adaptive_learner.py" "%APP_DIR%\" >nul
copy /y "%~dp0text_injector.py" "%APP_DIR%\" >nul
copy /y "%~dp0sync.py" "%APP_DIR%\" >nul
copy /y "%~dp0ui\*.py" "%APP_DIR%\ui\" >nul
copy /y "%~dp0voixclaire.ico" "%INSTALL_DIR%\" >nul

:: ===== 5. Modele Whisper =====
echo   [5/6] Telechargement du modele vocal (~500Mo, premiere fois)...
"%INSTALL_DIR%\python\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('         Modele pret !')"

:: ===== 6. Creer les raccourcis =====
echo   [6/6] Creation des raccourcis...

:: Creer le lanceur .bat cache
(
echo @echo off
echo start "" "%INSTALL_DIR%\python\pythonw.exe" "%APP_DIR%\main.py"
) > "%INSTALL_DIR%\lancer.bat"

:: Creer un .vbs pour lancer sans fenetre console (invisible)
(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo WshShell.Run """%INSTALL_DIR%\python\pythonw.exe"" ""%APP_DIR%\main.py""", 0, False
) > "%INSTALL_DIR%\VoixClaire.vbs"

:: Creer le raccourci Bureau via PowerShell
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'VoixClaire.lnk')); $s.TargetPath = '%INSTALL_DIR%\VoixClaire.vbs'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'VoixClaire - Reconnaissance vocale'; $s.IconLocation = '%INSTALL_DIR%\voixclaire.ico,0'; $s.Save()"

:: Creer le raccourci dans le menu Demarrer (epingle possible)
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTMENU%\VoixClaire.lnk'); $s.TargetPath = '%INSTALL_DIR%\VoixClaire.vbs'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'VoixClaire - Reconnaissance vocale'; $s.IconLocation = '%INSTALL_DIR%\voixclaire.ico,0'; $s.Save()"

:: Creer le raccourci dans la barre des taches
set "TASKBAR=%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
if exist "%TASKBAR%" (
    powershell -NoProfile -Command ^
      "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%TASKBAR%\VoixClaire.lnk'); $s.TargetPath = '%INSTALL_DIR%\VoixClaire.vbs'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'VoixClaire - Reconnaissance vocale'; $s.IconLocation = '%INSTALL_DIR%\voixclaire.ico,0'; $s.Save()"
)

:: Nettoyage
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║           Installation terminee !            ║
echo   ╠══════════════════════════════════════════════╣
echo   ║                                              ║
echo   ║  Raccourci "VoixClaire" cree sur :           ║
echo   ║    - Le Bureau                               ║
echo   ║    - Le Menu Demarrer                        ║
echo   ║                                              ║
echo   ║  Un double-clic et ca marche !               ║
echo   ║                                              ║
echo   ║  Astuce : clic droit sur le raccourci du     ║
echo   ║  Menu Demarrer pour l'epingler a la barre    ║
echo   ║  des taches.                                 ║
echo   ║                                              ║
echo   ╚══════════════════════════════════════════════╝
echo.

:: Proposer de lancer maintenant
set /p LAUNCH="  Lancer VoixClaire maintenant ? (O/N) : "
if /i "%LAUNCH%"=="O" (
    start "" "%INSTALL_DIR%\VoixClaire.vbs"
)

pause
