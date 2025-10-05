#!/usr/bin/env python3
"""
Script de diagnostic de vitesse
================================

Ce script mesure précisément où le temps est passé pendant la conversion.
"""

import time
import sys

print("="*60)
print("🔍 DIAGNOSTIC DE VITESSE - NASA Image Converter")
print("="*60)
print()

# 1. Vérifier VIPS
print("[1/5] Vérification de VIPS...")
try:
    import pyvips
    vips_version = f"v{pyvips.version(0)}.{pyvips.version(1)}"
    print(f"    ✅ VIPS disponible: {vips_version}")
    vips_available = True
except (ImportError, OSError) as e:
    print(f"    ❌ VIPS non disponible: {e}")
    print("    ⚠️  La conversion sera LENTE sans VIPS!")
    vips_available = False
print()

# 2. Vérifier la configuration
print("[2/5] Vérification de la configuration...")
try:
    from config_fast import FastProcessingConfig
    config = FastProcessingConfig()
    print(f"    ✅ Configuration RAPIDE chargée")
    print(f"    - use_vips: {config.CONVERSION_SETTINGS.get('use_vips', False)}")
    print(f"    - vips_threshold: {config.CONVERSION_SETTINGS.get('vips_threshold_pixels', 'N/A')} pixels")
    print(f"    - use_clahe: {config.CONVERSION_SETTINGS.get('use_clahe', True)}")
    print(f"    - enhance_contrast: {config.CONVERSION_SETTINGS.get('enhance_contrast', True)}")
    print(f"    - enhance_sharpness: {config.CONVERSION_SETTINGS.get('enhance_sharpness', True)}")
    print(f"    - tiff_compression: {config.CONVERSION_SETTINGS.get('tiff_compression', 'N/A')}")
except ImportError as e:
    print(f"    ❌ Erreur config_fast: {e}")
    from config import ProcessingConfig
    config = ProcessingConfig()
    print(f"    ⚠️  Configuration STANDARD chargée (plus lente)")
print()

# 3. Vérifier le convertisseur
print("[3/5] Vérification du convertisseur...")
try:
    from simple_converter import ImageConverter
    converter = ImageConverter(config)
    print(f"    ✅ ImageConverter initialisé")
    print(f"    - VIPS activé dans converter: {converter.vips_available}")
except Exception as e:
    print(f"    ❌ Erreur: {e}")
    sys.exit(1)
print()

# 4. Test de vitesse (si un fichier est fourni)
print("[4/5] Test de vitesse...")
if len(sys.argv) > 1:
    test_file = sys.argv[1]
    print(f"    📁 Fichier de test: {test_file}")
    
    import os
    if not os.path.exists(test_file):
        print(f"    ❌ Fichier non trouvé: {test_file}")
    else:
        file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
        print(f"    📊 Taille: {file_size_mb:.2f} MB")
        
        output_file = "test_output.tif"
        
        print(f"    ⏱️  Démarrage de la conversion...")
        start_time = time.time()
        
        try:
            success = converter.convert_file(test_file, output_file, format='TIFF')
            elapsed = time.time() - start_time
            
            if success:
                output_size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"    ✅ Conversion réussie!")
                print(f"    ⏱️  Temps total: {elapsed:.2f}s")
                print(f"    📊 Vitesse: {file_size_mb/elapsed:.2f} MB/s")
                print(f"    📊 Taille sortie: {output_size_mb:.2f} MB")
                
                # Évaluation
                if vips_available:
                    if elapsed < 10:
                        print(f"    🚀 EXCELLENT! Vitesse optimale avec VIPS")
                    elif elapsed < 30:
                        print(f"    ✅ BIEN! Vitesse correcte")
                    else:
                        print(f"    ⚠️  LENT! VIPS ne semble pas utilisé correctement")
                else:
                    print(f"    ⚠️  Lent mais normal sans VIPS (installez libvips!)")
            else:
                print(f"    ❌ Conversion échouée")
        except Exception as e:
            print(f"    ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
else:
    print("    ℹ️  Aucun fichier fourni pour le test")
    print("    Usage: python diagnostique_vitesse.py <fichier.img>")
print()

# 5. Recommandations
print("[5/5] Recommandations...")

if not vips_available:
    print("    ⚠️  PRIORITÉ #1: Installer libvips!")
    print("        1. Exécutez: install_vips.bat")
    print("        2. Ajoutez C:\\vips\\bin au PATH")
    print("        3. Redémarrez le terminal")
    print("        → Gain attendu: 5-10x plus rapide")
    print()

if config.CONVERSION_SETTINGS.get('use_clahe', True):
    print("    💡 CLAHE est activé (coûteux)")
    print("        - Désactivez dans config_fast.py pour +20% vitesse")
    print()

if config.CONVERSION_SETTINGS.get('enhance_contrast', True):
    print("    💡 Amélioration contraste activée")
    print("        - Désactivez pour +10% vitesse")
    print()

if config.CONVERSION_SETTINGS.get('tiff_compression') == 'lzw':
    print("    💡 Compression LZW (lente)")
    print("        - Utilisez 'jpeg' pour +30% vitesse")
    print()

threshold = config.CONVERSION_SETTINGS.get('vips_threshold_pixels', 10_000_000)
if threshold > 5_000_000:
    print(f"    💡 Seuil VIPS élevé ({threshold:,} pixels)")
    print("        - Réduisez à 1,000,000 pour utiliser VIPS plus souvent")
    print()

print()
print("="*60)
print("RÉSUMÉ")
print("="*60)

score = 0
if vips_available:
    score += 50
    print("✅ VIPS installé (+50 points)")
else:
    print("❌ VIPS manquant (0 points) - INSTALLEZ-LE!")

if not config.CONVERSION_SETTINGS.get('use_clahe', True):
    score += 20
    print("✅ CLAHE désactivé (+20 points)")
else:
    print("⚠️  CLAHE activé (0 points)")

if not config.CONVERSION_SETTINGS.get('enhance_contrast', True):
    score += 10
    print("✅ Contraste désactivé (+10 points)")

if not config.CONVERSION_SETTINGS.get('enhance_sharpness', True):
    score += 10
    print("✅ Netteté désactivée (+10 points)")

if config.CONVERSION_SETTINGS.get('tiff_compression') == 'jpeg':
    score += 10
    print("✅ Compression JPEG rapide (+10 points)")

print()
print(f"SCORE TOTAL: {score}/100")
print()

if score >= 90:
    print("🚀 CONFIGURATION OPTIMALE!")
elif score >= 70:
    print("✅ Bonne configuration, mais peut être améliorée")
elif score >= 50:
    print("⚠️  Configuration moyenne, optimisations recommandées")
else:
    print("❌ Configuration non optimisée, beaucoup d'améliorations possibles")

print()
print("Pour améliorer:")
print("1. Installez libvips (si pas fait): install_vips.bat")
print("2. Vérifiez que config_fast.py est utilisé dans app.py")
print("3. Relancez ce diagnostic pour voir les améliorations")
print()
