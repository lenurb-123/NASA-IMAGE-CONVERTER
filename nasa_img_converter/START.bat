@echo off
REM ========================================
REM NASA IMAGE CONVERTER - LANCEMENT RAPIDE
REM ========================================

echo.
echo ========================================
echo   NASA IMAGE CONVERTER
echo   Interface WOW - Production Ready
echo ========================================
echo.

REM Vérifier si le venv existe
if not exist "%USERPROFILE%\venv\Scripts\activate.bat" (
    echo [ERREUR] Environnement virtuel non trouve!
    echo.
    echo Creez-le avec: python -m venv %USERPROFILE%\venv
    echo Puis installez les dependances: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
echo [1/4] Activation de l'environnement virtuel...
call "%USERPROFILE%\venv\Scripts\activate.bat"
echo     OK
echo.

REM Vérifier VIPS
echo [2/4] Verification de VIPS...
python -c "import pyvips; print('     VIPS v' + str(pyvips.version(0)) + '.' + str(pyvips.version(1)) + ' OK')" 2>nul
if errorlevel 1 (
    echo     VIPS non disponible ^(conversion plus lente^)
    echo     Installez avec: install_vips.bat
) else (
    echo     VIPS detecte! Conversion ultra-rapide activee!
)
echo.

REM Vérifier les dossiers
echo [3/4] Creation des dossiers necessaires...
if not exist "static\css" mkdir static\css
if not exist "static\js" mkdir static\js
if not exist "temp_uploads" mkdir temp_uploads
if not exist "cache" mkdir cache
echo     OK
echo.

REM Lancer l'application
echo [4/4] Demarrage de l'application...
echo.
echo ========================================
echo   APPLICATION DEMARREE!
echo ========================================
echo.
echo   Interface web: http://localhost:5000
echo   Design moderne: ACTIVE
echo   VIPS: %VIPS_STATUS%
echo.
echo   Appuyez sur CTRL+C pour arreter
echo ========================================
echo.

python app.py

pause
