@echo off
REM ========================================
REM NETTOYAGE POUR DEPLOIEMENT
REM Supprime tous les dossiers/fichiers inutiles
REM ========================================

echo.
echo ========================================
echo   NETTOYAGE AVANT DEPLOIEMENT
echo ========================================
echo.

REM Supprimer les dossiers de cache et temp
echo [1/3] Suppression des dossiers temporaires...
if exist "cache" (
    rmdir /s /q "cache"
    echo     cache/ supprime
)
if exist "cache_tiff" (
    rmdir /s /q "cache_tiff"
    echo     cache_tiff/ supprime
)
if exist "temp_uploads" (
    rmdir /s /q "temp_uploads"
    echo     temp_uploads/ supprime
)
if exist "temp_downloads" (
    rmdir /s /q "temp_downloads"
    echo     temp_downloads/ supprime
)
if exist "output_images" (
    rmdir /s /q "output_images"
    echo     output_images/ supprime
)
if exist "input_images" (
    rmdir /s /q "input_images"
    echo     input_images/ supprime
)
if exist "dzi_tiles" (
    rmdir /s /q "dzi_tiles"
    echo     dzi_tiles/ supprime
)
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    echo     __pycache__/ supprime
)
if exist "venv" (
    rmdir /s /q "venv"
    echo     venv/ supprime
)
echo.

REM Supprimer les fichiers inutiles
echo [2/3] Suppression des fichiers inutiles...
if exist "vips.zip" (
    del "vips.zip"
    echo     vips.zip supprime
)
if exist "install_vips.bat" (
    del "install_vips.bat"
    echo     install_vips.bat supprime
)
if exist "START.bat" (
    del "START.bat"
    echo     START.bat supprime
)
if exist "diagnostique_vitesse.py" (
    del "diagnostique_vitesse.py"
    echo     diagnostique_vitesse.py supprime
)
echo.

REM Vérifier les fichiers essentiels
echo [3/3] Verification des fichiers essentiels...
set MISSING=0

if not exist "app.py" (
    echo     [ERREUR] app.py manquant!
    set MISSING=1
)
if not exist "requirements.txt" (
    echo     [ERREUR] requirements.txt manquant!
    set MISSING=1
)
if not exist "render.yaml" (
    echo     [ERREUR] render.yaml manquant!
    set MISSING=1
)
if not exist "templates\index.html" (
    echo     [ERREUR] templates/index.html manquant!
    set MISSING=1
)

if %MISSING%==0 (
    echo     Tous les fichiers essentiels sont presents!
) else (
    echo.
    echo     [ATTENTION] Certains fichiers essentiels manquent!
    pause
    exit /b 1
)
echo.

echo ========================================
echo   NETTOYAGE TERMINE!
echo ========================================
echo.
echo   Fichiers gardes:
echo   - app.py, simple_converter.py, streaming_converter.py
echo   - config.py, config_fast.py
echo   - requirements.txt, render.yaml
echo   - README.md, .gitignore
echo   - templates/ et static/
echo.
echo   Pret pour deploiement sur Render/Railway/Vercel!
echo.
echo   Prochaines etapes:
echo   1. git init
echo   2. git add .
echo   3. git commit -m "Initial commit"
echo   4. Creer repo GitHub
echo   5. git push
echo   6. Deployer sur Render.com
echo.
pause
