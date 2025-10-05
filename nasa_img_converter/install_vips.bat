@echo off
echo Installation de VIPS pour traitement d'images rapide...
echo.

REM Télécharger et installer VIPS pour Windows
echo [1/3] Téléchargement de VIPS...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/libvips/libvips/releases/download/v8.15.2/vips-dev-w64-all-8.15.2.zip' -OutFile 'vips.zip'"

echo [2/3] Décompression...
powershell -Command "Expand-Archive -Path 'vips.zip' -DestinationPath 'C:\vips' -Force"

echo [3/3] Configuration des variables d'environnement...
setx VIPS_HOME "C:\vips"
setx PATH "%PATH%;C:\vips\bin"

echo.
echo VIPS installe! Redémarrez votre terminal.
echo Vous pouvez maintenant lancer START.bat
pause
