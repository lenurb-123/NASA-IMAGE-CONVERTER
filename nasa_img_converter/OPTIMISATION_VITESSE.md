# Guide d'optimisation - NASA Image Converter

## Optimisations de performance

### VIPS Integration
- pyvips pour traitement 5-10x plus rapide
- Mémoire optimisée pour grandes images
- Streaming pour fichiers volumineux

### Cache intelligent
- Cache TIFF pour éviter reconversions
- Cache PNG pour prévisualisations
- Nettoyage automatique des anciens fichiers

### Téléchargement robuste
- Reprise automatique sur erreur
- Support Range requests
- Timeout configurable

## Configuration recommandée

Pour les meilleures performances :
- Activer VIPS avec install_vips.bat
- Utiliser SSD pour le cache
- Configurer max_workers selon votre CPU
