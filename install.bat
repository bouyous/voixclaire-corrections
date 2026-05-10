@echo off
echo.
echo   VoixClaire - Installation rapide
echo   =================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Python n'est pas installe !
    echo   Telecharge-le ici : https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Python detecte. Installation des dependances...
echo.
python -m pip install --upgrade pip -q 2>nul
python -m pip install faster-whisper PyQt6 sounddevice numpy scipy librosa scikit-learn pynput pyperclip -q

if %errorlevel% neq 0 (
    echo.
    echo   Erreur lors de l'installation des dependances.
    pause
    exit /b 1
)

echo.
echo   Dependances installees !
echo.
echo   Telechargement du modele vocal (~500Mo, premiere fois)...
python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8'); print('   Modele pret !')"

echo.
echo   =================================
echo   Installation terminee !
echo   Lance "lancer.bat" pour demarrer.
echo   =================================
echo.
pause
