# NASA Image Converter

Convertisseur d'images NASA PDS vers formats modernes avec interface web.

## Installation

1. Cloner le projet
2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancer l'application :
   ```bash
   python app.py
   ```

## Utilisation

1. Ouvrir http://localhost:5000
2. Coller l'URL d'une image NASA PDS
3. Cliquer sur "Convertir"
4. Télécharger l'image convertie en TIFF

## Technologies

- Flask
- PIL/Pillow
- OpenCV
- pyvips
- pdr (PDS3)
- planetaryimage (PDS4)

## Auteur

NASA Image Converter Team
