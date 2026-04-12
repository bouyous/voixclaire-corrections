@echo off
chcp 65001 >nul
echo.
echo   ╔══════════════════════════════════════╗
echo   ║     VoixClaire - Installation        ║
echo   ║  Reconnaissance vocale adaptative    ║
echo   ╚══════════════════════════════════════╝
echo.

:: Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Python n'est pas installe.
    echo.
    echo   Telecharge Python ici :
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANT : Coche "Add Python to PATH" !
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   [OK] Python %PYVER% detecte
echo.

:: Environnement virtuel
if not exist "venv" (
    echo   [1/3] Creation de l'environnement virtuel...
    python -m venv venv
) else (
    echo   [1/3] Environnement virtuel existe deja.
)

call venv\Scripts\activate.bat

:: Dependances
echo   [2/3] Installation des dependances...
echo         (ca peut prendre quelques minutes la premiere fois)
pip install --upgrade pip -q
pip install -r requirements.txt -q

:: Modele Whisper
echo   [3/3] Telechargement du modele de reconnaissance vocale...
echo         (environ 500 Mo la premiere fois)
python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('         Modele pret !')"

echo.
echo   ╔══════════════════════════════════════╗
echo   ║       Installation terminee !        ║
echo   ║                                      ║
echo   ║  Double-clique sur "lancer.bat"      ║
echo   ║  pour demarrer VoixClaire            ║
echo   ╚══════════════════════════════════════╝
echo.
pause
