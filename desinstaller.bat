@echo off
chcp 65001 >nul

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║   VoixClaire - Desinstallation           ║
echo   ╚══════════════════════════════════════════╝
echo.
echo   Cela va supprimer VoixClaire de ce PC.
echo   Les corrections apprises seront conservees
echo   sur GitHub et sur la cle USB.
echo.

set /p CONFIRM="  Continuer ? (O/N) : "
if /i not "%CONFIRM%"=="O" (
    echo   Annule.
    pause
    exit /b 0
)

set "INSTALL_DIR=%LOCALAPPDATA%\VoixClaire"

:: Supprimer les raccourcis
del /f /q "%USERPROFILE%\Desktop\VoixClaire.lnk" 2>nul
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\VoixClaire.lnk" 2>nul
del /f /q "%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\VoixClaire.lnk" 2>nul

:: Supprimer l'installation
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo   [OK] Fichiers supprimes.
) else (
    echo   VoixClaire n'etait pas installe.
)

echo.
echo   Desinstallation terminee.
echo   Les donnees dans %%APPDATA%%\VoixClaire ont ete conservees.
echo.
pause
