# NASA Image Converter - Description du projet

## Vue d'ensemble
Application web Flask pour convertir les images NASA PDS en formats modernes (TIFF, PNG).

## Fonctionnalités principales
- Téléchargement d'URLs d'images NASA
- Conversion automatique PDS3/PDS4 vers TIFF
- Mise en cache intelligente
- Interface web moderne
- Traitement par lots
- Support Deep Zoom pour les grandes images

## Architecture
- **Frontend** : HTML5/CSS3/JavaScript moderne
- **Backend** : Flask avec traitement d'images optimisé
- **Traitement** : pyvips pour les performances, fallbacks disponibles
- **Formats** : Support PDS3/PDS4 via pdr et planetaryimage
