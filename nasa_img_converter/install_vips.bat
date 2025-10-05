@echo off
REM Installation automatique de libvips sur Windows
REM Exécuter en tant qu'administrateur pour ajouter au PATH système

echo ========================================
echo Installation de libvips pour Windows
echo ========================================
echo.

REM Télécharger libvips
echo [1/4] Téléchargement de libvips 8.15.1...
curl -L https://github.com/libvips/build-win64-mxe/releases/download/v8.15.1/vips-dev-w64-all-8.15.1.zip -o vips.zip
if errorlevel 1 (
    echo ERREUR: Échec du téléchargement
    pause
    exit /b 1
)
echo ✅ Téléchargement terminé
echo.

REM Extraire
echo [2/4] Extraction dans C:\vips...
powershell -command "Expand-Archive -Path vips.zip -DestinationPath C:\ -Force"
if errorlevel 1 (
    echo ERREUR: Échec de l'extraction
    pause
    exit /b 1
)
echo ✅ Extraction terminée
echo.

REM Renommer
echo [3/4] Configuration du dossier...
if exist "C:\vips" (
    rmdir /s /q "C:\vips"
)
move "C:\vips-dev-8.15" "C:\vips" >nul 2>&1
echo ✅ Configuration terminée
echo.

REM Ajouter au PATH
echo [4/4] Ajout au PATH système...
setx PATH "%PATH%;C:\vips\bin" /M >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Impossible d'ajouter au PATH système (droits admin requis)
    echo.
    echo 📝 Veuillez ajouter manuellement C:\vips\bin au PATH:
    echo    1. Windows + Rechercher "variables d'environnement"
    echo    2. Variables système -^> Path -^> Modifier
    echo    3. Nouveau -^> C:\vips\bin
    echo    4. OK -^> OK -^> OK
) else (
    echo ✅ PATH mis à jour
)
echo.

REM Nettoyer
echo Nettoyage...
del vips.zip >nul 2>&1
echo.

REM Vérification
echo ========================================
echo Installation terminée!
echo ========================================
echo.
echo 📝 IMPORTANT: Redémarrez votre terminal pour appliquer les changements
echo.
echo 🧪 Pour vérifier l'installation, dans un NOUVEAU terminal:
echo    python -c "import pyvips; print(f'VIPS v{pyvips.version(0)}.{pyvips.version(1)} ✅')"
echo.
pause
