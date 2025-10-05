# NASA IMAGE CONVERTER - Guide de déploiement

## Prérequis
- Python 3.8+
- Git
- Compte Vercel

## Étapes de déploiement

1. **Préparer le projet**
   - S'assurer que `requirements.txt` contient toutes les dépendances
   - Vérifier que `vercel.json` est configuré correctement

2. **Déploiement sur Vercel**
   - Connecter le repository Git à Vercel
   - Configurer les paramètres de build
   - Déployer

## Configuration requise

Pour le déploiement réussi sur Vercel, certaines dépendances doivent être ajustées :
- Utiliser `opencv-python-headless` au lieu de `opencv-python`
- Supprimer `pdr` si nécessaire pour réduire la taille
- Utiliser `packages.txt` pour les dépendances système
