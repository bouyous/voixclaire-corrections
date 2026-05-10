@echo off
chcp 65001 >nul
echo.
echo   Construction de VoixClaire.exe...
echo.

call venv\Scripts\activate.bat

pip install pyinstaller -q

pyinstaller --noconfirm --onedir --windowed ^
    --name "VoixClaire" ^
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
echo   Executable cree dans : dist\VoixClaire\VoixClaire.exe
echo.
echo   Pour distribuer, copiez tout le dossier dist\VoixClaire\
echo   Le modele Whisper sera telecharge au premier lancement.
echo.
pause
