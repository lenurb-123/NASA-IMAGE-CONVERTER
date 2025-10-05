import os
import requests
import io
import json
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from PIL import Image
import pvl
import numpy as np
from io import BytesIO
import tempfile
import hashlib
from functools import lru_cache
from pathlib import Path
import gc

from config import ProcessingConfig
from simple_converter import ImageConverter
from streaming_converter import StreamingConverter

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['CACHE_FOLDER'] = 'cache'

# Static files configuration for modern design
app.static_folder = 'static'
app.static_url_path = '/static'

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CACHE_FOLDER'], exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

# Initialize processors with optimized config
# Automatically uses FastProcessingConfig if available
try:
    from config_fast import FastProcessingConfig
    config = FastProcessingConfig()
    print("[INFO] 🚀 FAST Configuration enabled (FastProcessingConfig)")
    print("[INFO] Expect 5-10x faster conversion with VIPS!")
except ImportError:
    config = ProcessingConfig()
    print("[INFO] ⚙️  Standard configuration enabled")

image_converter = ImageConverter(config)
streaming_converter = StreamingConverter(config)

def detect_pds_version(content):
    """Detects if file is in PDS3 or PDS4 format by analyzing the first lines."""
    try:
        # Read first lines
        lines = content.decode('latin-1').split('\n')[:20]
        header = '\n'.join(lines)
        
        # Check for PDS3 and PDS4 markers
        if any(marker in header for marker in ['PDS_VERSION_ID', 'PDS3']):
            return 'PDS3'
        elif any(marker in header for marker in ['PDS4', '<?xml', 'pds:']):
            return 'PDS4'
        return 'Unknown'
    except Exception as e:
        return f'Detection error: {str(e)}'

def normalize_image_data(img_data):
    """Normalizes image data in an optimized and memory-efficient way."""
    print(f"[DEBUG] Normalisation - dtype: {img_data.dtype}, shape: {img_data.shape}")
    print(f"[DEBUG] Valeurs - min: {img_data.min()}, max: {img_data.max()}, mean: {img_data.mean():.2f}")
    
    # If already in uint8 with good range, no need to normalize
    if img_data.dtype == np.uint8:
        img_min = img_data.min()
        img_max = img_data.max()
        
        # Si l'image a déjà un bon contraste, la retourner telle quelle
        if img_max > 200 and img_min < 50:
            print("[DEBUG] Image déjà bien contrastée, pas de normalisation")
            return img_data
    
    # Utiliser des percentiles pour éviter les valeurs aberrantes
    # Échantillonnage pour économiser la mémoire sur les grandes images
    if img_data.size > 10_000_000:  # Plus de 10M pixels
        print("[DEBUG] Grande image, échantillonnage pour les percentiles...")
        sample = img_data.ravel()[::100]  # Échantillonner 1 pixel sur 100
        p_low = np.percentile(sample, 2)
        p_high = np.percentile(sample, 98)
    else:
        p_low = np.percentile(img_data, 2)
        p_high = np.percentile(img_data, 98)
    
    print(f"[DEBUG] Percentiles - 2%: {p_low}, 98%: {p_high}")
    
    if p_high - p_low > 0:
        # Normalisation IN-PLACE pour économiser la mémoire (utiliser float32 au lieu de float64)
        if img_data.dtype != np.float32:
            img_data = img_data.astype(np.float32)
        
        # Clipping et normalisation en une seule passe
        np.clip(img_data, p_low, p_high, out=img_data)
        img_data -= p_low
        img_data *= (255.0 / (p_high - p_low))
        
        # Conversion finale en uint8
        result = img_data.astype(np.uint8)
        print(f"[DEBUG] Après normalisation - min: {result.min()}, max: {result.max()}")
        return result
    else:
        print("[DEBUG] Pas de variation dans l'image")
        return np.zeros_like(img_data, dtype=np.uint8)

def convert_pds_to_image(file_path, pds_version, max_dimension=None):
    """Convertit un fichier PDS en image PNG avec optimisations mémoire et performance.
    
    Args:
        file_path: Chemin vers le fichier PDS
        pds_version: Version PDS (PDS3 ou PDS4)
        max_dimension: Dimension maximale pour le redimensionnement (None = pas de redimensionnement)
    """
    try:
        if pds_version == 'PDS3':
            # Pour PDS3, nous utilisons pdr (compatible NumPy 2.x)
            try:
                import pdr
                
                # Charger l'image PDS3 avec pdr
                print(f"[INFO] Chargement avec pdr...")
                data = pdr.read(file_path)
                
                # Extraire les données d'image
                if hasattr(data, 'IMAGE'):
                    img_data = np.array(data.IMAGE, copy=False)
                elif hasattr(data, 'image'):
                    img_data = np.array(data.image, copy=False)
                else:
                    # Essayer de trouver le premier array
                    for key in dir(data):
                        attr = getattr(data, key)
                        if isinstance(attr, np.ndarray) and attr.ndim >= 2:
                            img_data = attr
                            break
                    else:
                        return "Impossible de trouver les données d'image dans le fichier PDS"
                
                print(f"[INFO] Image chargée: shape={img_data.shape}, dtype={img_data.dtype}")
                
                # Pour les très grandes images, redimensionner AVANT le traitement pour économiser la RAM
                if max_dimension and max(img_data.shape) > max_dimension * 2:
                    print(f"[INFO] Image très grande, pré-redimensionnement pour économiser la mémoire...")
                    from PIL import Image as PILImage
                    
                    # Créer une image PIL temporaire
                    if len(img_data.shape) == 2:
                        temp_img = PILImage.fromarray(img_data, 'L')
                    else:
                        temp_img = PILImage.fromarray(img_data, 'RGB')
                    
                    # Redimensionner
                    temp_img.thumbnail((max_dimension * 2, max_dimension * 2), PILImage.Resampling.LANCZOS)
                    
                    # Reconvertir en array
                    img_data = np.array(temp_img)
                    del temp_img
                    print(f"[INFO] Nouvelle taille: {img_data.shape}")
                
            except Exception as e:
                # Fallback vers planetaryimage si pdr échoue
                print(f"[WARNING] Erreur pdr: {e}, essai avec planetaryimage...")
                try:
                    from planetaryimage import PDS3Image
                    pds_img = PDS3Image.open(file_path)
                    img_data = np.array(pds_img.image, copy=False)
                except Exception as e2:
                    return f"Erreur de lecture PDS3: {str(e2)}"
            
            # Normaliser les données de manière optimisée
            img_data = normalize_image_data(img_data)
            
            # Améliorer le contraste de manière scientifiquement appropriée
            # CLAHE préserve les détails tout en améliorant la visibilité
            try:
                import cv2
                print("[INFO] Application de CLAHE (préservation des données scientifiques)...")
                # clipLimit plus bas pour préserver les vraies valeurs
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                
                if len(img_data.shape) == 2:
                    # Image en niveaux de gris (typique des images NASA)
                    img_data = clahe.apply(img_data)
                else:
                    # Image couleur - appliquer sur chaque canal indépendamment
                    for i in range(img_data.shape[2]):
                        img_data[:, :, i] = clahe.apply(img_data[:, :, i])
                
                print(f"[INFO] Après CLAHE - min: {img_data.min()}, max: {img_data.max()}")
            except ImportError:
                print("[WARNING] OpenCV non disponible, amélioration basique")
            except Exception as e:
                print(f"[WARNING] Erreur CLAHE: {e}")
            
            # Créer une image PIL
            if len(img_data.shape) == 2:  # Image en niveaux de gris
                img = Image.fromarray(img_data, 'L')
                print("[INFO] Image en niveaux de gris (monochrome)")
            else:  # Image couleur
                img = Image.fromarray(img_data, 'RGB')
                print(f"[INFO] Image couleur ({img_data.shape[2]} canaux)")
            
            # Amélioration légère avec PIL pour la clarté (sans dénaturer)
            from PIL import ImageEnhance
            
            # Contraste modéré pour améliorer la lisibilité
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.15)  # +15% seulement
            
            # Netteté légère pour les détails
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)  # +10% seulement
            
            print("[INFO] Améliorations appliquées (préservation des couleurs scientifiques)")
            
            # Libérer la mémoire
            del img_data
            gc.collect()
            
            # Redimensionner si nécessaire pour accélérer l'affichage
            if max_dimension and max(img.size) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Sauvegarder en mémoire avec compression optimisée
            img_io = BytesIO()
            # Utiliser compress_level pour un meilleur équilibre vitesse/taille
            img.save(img_io, 'PNG', optimize=False, compress_level=6)
            img_io.seek(0)
            
            # Libérer la mémoire de l'image PIL
            del img
            gc.collect()
            
            return img_io
            
        elif pds_version == 'PDS4':
            # Pour PDS4, utiliser la même bibliothèque
            from planetaryimage import PDS4Image
            
            try:
                pds_img = PDS4Image.open(file_path)
                img_data = np.array(pds_img.image, copy=False)
                
                # Normaliser les données de manière optimisée
                img_data = normalize_image_data(img_data)
                
                # Créer une image PIL
                if len(img_data.shape) == 2:
                    img = Image.fromarray(img_data, 'L')
                else:
                    img = Image.fromarray(img_data, 'RGB')
                
                del img_data, pds_img
                gc.collect()
                
                # Redimensionner si nécessaire
                if max_dimension and max(img.size) > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                img_io = BytesIO()
                img.save(img_io, 'PNG', optimize=False, compress_level=6)
                img_io.seek(0)
                del img
                gc.collect()
                
                return img_io
            except Exception as e:
                return f"Erreur PDS4: {str(e)}. Le support PDS4 peut être limité."
            
    except Exception as e:
        return f'Erreur lors de la conversion: {str(e)}'

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def get_cache_key(url):
    """Génère une clé de cache unique pour une URL."""
    return hashlib.md5(url.encode()).hexdigest()

def get_cached_image(cache_key):
    """Récupère une image TIFF depuis le cache si elle existe."""
    cache_path = os.path.join(app.config['CACHE_FOLDER'], f"{cache_key}.tif")
    if os.path.exists(cache_path):
        return cache_path
    return None

def get_cache_file_path(cache_key):
    """Construit le chemin du fichier TIFF en cache."""
    return os.path.join(app.config['CACHE_FOLDER'], f"{cache_key}.tif")

@app.route('/process', methods=['POST'])
def process_image():
    temp_file = None
    try:
        # Vérifier si une URL a été fournie
        print("[DEBUG] ==================== NOUVELLE REQUÊTE ====================")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] Form data keys: {list(request.form.keys())}")
        print(f"[DEBUG] Form data: {dict(request.form)}")
        
        if 'url' not in request.form or not request.form['url']:
            print("[ERROR] Aucune URL fournie dans le formulaire")
            print(f"[ERROR] Données reçues: {dict(request.form)}")
            return jsonify({'error': 'Aucune URL fournie. Vérifiez que le champ est rempli.'}), 400
            
        url = request.form['url'].strip()
        print(f"[INFO] ✅ URL reçue: {url}")
        print(f"[INFO] Longueur URL: {len(url)} caractères")
        
        # Vérifier le cache d'abord
        cache_key = get_cache_key(url)
        cached_image = get_cached_image(cache_key)
        
        if cached_image:
            # Retourner l'image depuis le cache (TIFF)
            response_obj = send_file(
                cached_image,
                mimetype='image/tiff',
                as_attachment=False,
                download_name='nasa_image.tif'
            )
            response_obj.headers['X-PDS-Version'] = 'Cached'
            response_obj.headers['X-Cache-Hit'] = 'true'
            return response_obj
        
        # Télécharger le fichier (prélecture pour détection)
        print(f"[INFO] Téléchargement de l'image (prélecture pour détection)...")
        response = requests.get(
            url,
            stream=True,
            timeout=300,
            headers={'Accept-Encoding': 'gzip, deflate'}
        )
        response.raise_for_status()
        print(f"[INFO] Téléchargement réussi, status: {response.status_code}")
        
        # Vérifier la taille du fichier
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 500 * 1024 * 1024:
            return jsonify({'error': 'Le fichier dépasse la limite de 500 Mo'}), 400
        
        # Lire les premières données pour la détection PDS (chunk plus grand)
        print("[INFO] Lecture des premières données...")
        first_chunk = b''
        chunk_iter = response.iter_content(chunk_size=65536)  # 64KB chunks
        try:
            for chunk in chunk_iter:
                first_chunk += chunk
                if len(first_chunk) >= 10000:  # Suffisant pour détecter le format
                    break
            print(f"[INFO] Premier chunk lu: {len(first_chunk)} bytes")
        except Exception as e:
            print(f"[ERROR] Erreur lecture chunk: {e}")
            return jsonify({'error': f'Erreur lecture des données: {str(e)}'}), 400
        
        # Détecter la version PDS
        print("[INFO] Détection de la version PDS...")
        pds_version = detect_pds_version(first_chunk)
        print(f"[INFO] Version PDS détectée: {pds_version}")
        
        if pds_version.startswith('Erreur'):
            return jsonify({'error': pds_version}), 400
        
        # Créer un fichier temporaire et amorcer avec le premier chunk
        print("[INFO] Création du fichier temporaire...")
        temp_fd, temp_file = tempfile.mkstemp(suffix='.img', dir=app.config['UPLOAD_FOLDER'])
        print(f"[INFO] Fichier temporaire: {temp_file}")
        try:
            with os.fdopen(temp_fd, 'wb', buffering=262144) as f:
                f.write(first_chunk)
        except Exception as e:
            print(f"[ERROR] Erreur d'initialisation fichier: {e}")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return jsonify({'error': f"Erreur écriture fichier: {str(e)}"}), 400

        # Reprendre le téléchargement de manière robuste (Range + retries)
        print("[INFO] Téléchargement robuste avec reprise (HTTP Range + retries)...")
        def prog(cur, total):
            try:
                pct = (cur / total) * 100 if total else 0
                if int(pct) % 10 == 0:
                    print(f"[INFO] Progression: {pct:.1f}% ({cur}/{total} bytes)")
            except Exception:
                pass
        ok = streaming_converter.download_with_resume(
            url=url,
            output_file=temp_file,
            progress_callback=prog,
            max_retries=5,
            backoff_factor=2.0
        )
        if not ok:
            print("[ERROR] Téléchargement échoué après reprises. Abort.")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return jsonify({'error': "Téléchargement interrompu par le serveur distant. Veuillez réessayer."}), 502
        
        # Convertir en TIFF et écrire dans le cache (gestion grandes images incluse dans ImageConverter)
        max_dimension = request.form.get('max_dimension', 8192, type=int)
        cache_file = get_cache_file_path(cache_key)
        print(f"[INFO] Conversion en TIFF vers cache: {cache_file} (max_dimension={max_dimension})")
        success = image_converter.convert_file(
            temp_file,
            cache_file,
            format='TIFF',
            enhance=True,
            max_dimension=max_dimension
        )
        
        # Nettoyer le fichier temporaire
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        
        if not success or not os.path.exists(cache_file):
            print("[ERROR] Echec de conversion en TIFF")
            return jsonify({'error': 'Echec de conversion en TIFF'}), 500
        
        # Envoyer le fichier TIFF depuis le cache
        print(f"[INFO] Envoi du TIFF au client...")
        response_obj = send_file(
            cache_file,
            mimetype='image/tiff',
            as_attachment=False,
            download_name='nasa_image.tif'
        )
        response_obj.headers['X-PDS-Version'] = pds_version
        response_obj.headers['X-Cache-Hit'] = 'false'
        print(f"[SUCCESS] Conversion réussie!")
        return response_obj
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout lors du téléchargement")
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({'error': 'Délai d\'attente dépassé lors du téléchargement'}), 408
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Erreur de requête: {str(e)}")
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({'error': f'Erreur de téléchargement: {str(e)}'}), 400
    except Exception as e:
        print(f"[ERROR] Exception non gérée: {str(e)}")
        import traceback
        traceback.print_exc()
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return jsonify({'error': str(e)}), 500

## Deep Zoom routes and functionality removed per requirement


## Lightweight image info endpoint removed


if __name__ == '__main__':
    # Configuration pour déploiement cloud (Render, Railway, etc.)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(
        host='0.0.0.0',  # Nécessaire pour déploiement
        port=port,
        debug=debug
    )
