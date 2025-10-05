# 🧹 Nettoyage pour Déploiement

## Fichiers/Dossiers à SUPPRIMER

### Dossiers Inutiles
```bash
# Supprimer ces dossiers (ne servent pas en production)
cache/
cache_tiff/
temp_uploads/
temp_downloads/
output_images/
input_images/
dzi_tiles/
__pycache__/
venv/
```

### Fichiers Inutiles
```bash
# Supprimer ces fichiers
install_vips.bat
START.bat
diagnostique_vitesse.py
vips.zip
DESIGN_UPGRADE.md
VITESSE_RAPIDE.md
OPTIMISATION_VITESSE.md
INTERFACE_WOW.md
```

### Fichiers à GARDER
```
✅ app.py
✅ simple_converter.py
✅ streaming_converter.py
✅ config.py
✅ config_fast.py
✅ requirements.txt
✅ README.md
✅ templates/index.html
✅ static/ (CSS/JS)
```

## Commandes de Nettoyage

```cmd
REM Dans le dossier nasa_img_converter
rmdir /s /q cache
rmdir /s /q cache_tiff
rmdir /s /q temp_uploads
rmdir /s /q temp_downloads
rmdir /s /q output_images
rmdir /s /q input_images
rmdir /s /q dzi_tiles
rmdir /s /q __pycache__
del vips.zip
```
