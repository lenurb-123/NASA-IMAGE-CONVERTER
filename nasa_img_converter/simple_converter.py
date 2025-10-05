"""
Simple Image Converter Module
==============================

This module handles basic conversion of scientific .IMG files to web-friendly formats
(PNG, JPEG, WebP) with optional visual enhancements while preserving scientific data integrity.

Author: NASA Image Converter Team
License: MIT
"""

import os
import gc
import logging
from pathlib import Path
from typing import Optional, Tuple, Union, List
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance
import cv2

from config import ProcessingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageConverter:
    """
    Main class for converting scientific image files to standard formats.
    
    This class handles:
    - Loading .IMG files (PDS3/PDS4 formats)
    - Normalization and enhancement
    - Conversion to PNG, JPEG, WebP
    - Error handling and validation
    
    Example:
        >>> converter = ImageConverter()
        >>> converter.convert_file('input.img', 'output.png', format='PNG')
        True
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize the ImageConverter.
        
        Args:
            config (ProcessingConfig, optional): Configuration object. 
                                                 Defaults to ProcessingConfig.
        """
        self.config = config or ProcessingConfig()
        self.conversion_settings = self.config.CONVERSION_SETTINGS
        self.memory_settings = self.config.MEMORY_SETTINGS
        self.pds_settings = self.config.PDS_SETTINGS
        
        # Try to load pyvips for better large image handling
        self.vips_available = False
        if self.conversion_settings.get('use_vips', True):
            try:
                import pyvips
                self.pyvips = pyvips
                self.vips_available = True
                # Set memory limit
                mem_limit = self.conversion_settings.get('vips_memory_limit_mb', 2000)
                pyvips.cache_set_max_mem(mem_limit * 1024 * 1024)
                logger.info(f"pyvips available (v{pyvips.version(0)}.{pyvips.version(1)})")
            except (ImportError, OSError) as e:
                logger.warning(f"pyvips not available: {e}. Will use PIL for all operations.")
                self.vips_available = False
        
    def detect_pds_version(self, file_path: Union[str, Path]) -> str:
        """
        Detect PDS version (PDS3 or PDS4) from file header.
        
        Args:
            file_path (str or Path): Path to the .IMG file
            
        Returns:
            str: 'PDS3', 'PDS4', or 'Unknown'
            
        Example:
            >>> converter = ImageConverter()
            >>> version = converter.detect_pds_version('mars_image.img')
            >>> print(version)
            'PDS3'
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(self.pds_settings['detection_chunk_size'])
                header_text = header.decode('latin-1', errors='ignore')
                
                # Check for PDS3 markers
                if any(marker in header_text for marker in ['PDS_VERSION_ID', 'PDS3']):
                    return 'PDS3'
                
                # Check for PDS4 markers
                elif any(marker in header_text for marker in ['PDS4', '<?xml', 'pds:']):
                    return 'PDS4'
                
                return 'Unknown'
                
        except Exception as e:
            logger.error(f"Error detecting PDS version: {e}")
            return 'Unknown'
    
    def load_pds_image(self, file_path: Union[str, Path], 
                       pds_version: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Load image data from PDS file.
        
        Args:
            file_path (str or Path): Path to the .IMG file
            pds_version (str, optional): PDS version ('PDS3' or 'PDS4'). 
                                        Auto-detected if None.
            
        Returns:
            np.ndarray or None: Image data as numpy array, or None on error
            
        Example:
            >>> converter = ImageConverter()
            >>> img_data = converter.load_pds_image('mars_surface.img')
            >>> print(img_data.shape)
            (2048, 2048)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Auto-detect PDS version if not provided
        if pds_version is None:
            pds_version = self.detect_pds_version(file_path)
            logger.info(f"Detected PDS version: {pds_version}")
        
        img_data = None
        
        try:
            if pds_version == 'PDS3':
                # Try pdr first (recommended for NumPy 2.x compatibility)
                try:
                    import pdr
                    logger.info(f"Loading {file_path} with pdr...")
                    data = pdr.read(str(file_path))
                    
                    # Extract image data
                    if hasattr(data, 'IMAGE'):
                        img_data = np.array(data.IMAGE, copy=False)
                    elif hasattr(data, 'image'):
                        img_data = np.array(data.image, copy=False)
                    else:
                        # Find first suitable array
                        for key in dir(data):
                            attr = getattr(data, key)
                            if isinstance(attr, np.ndarray) and attr.ndim >= 2:
                                img_data = attr
                                break
                    
                    if img_data is None:
                        raise ValueError("No image data found in PDS file")
                        
                except ImportError:
                    logger.warning("pdr not available, trying planetaryimage...")
                    from planetaryimage import PDS3Image
                    pds_img = PDS3Image.open(str(file_path))
                    img_data = np.array(pds_img.image, copy=False)
                    
            elif pds_version == 'PDS4':
                from planetaryimage import PDS4Image
                logger.info(f"Loading {file_path} with planetaryimage (PDS4)...")
                pds_img = PDS4Image.open(str(file_path))
                img_data = np.array(pds_img.image, copy=False)
            
            else:
                logger.error(f"Unsupported PDS version: {pds_version}")
                return None
            
            logger.info(f"Loaded image: shape={img_data.shape}, dtype={img_data.dtype}")
            return img_data
            
        except Exception as e:
            logger.error(f"Error loading PDS image: {e}")
            return None
    
    def normalize_image(self, img_data: np.ndarray) -> np.ndarray:
        """
        Normalize image data to 0-255 range using percentile-based scaling.
        
        This method preserves scientific data integrity by using percentiles
        to avoid outlier influence.
        
        Args:
            img_data (np.ndarray): Input image data
            
        Returns:
            np.ndarray: Normalized image data (uint8)
            
        Example:
            >>> converter = ImageConverter()
            >>> raw_data = np.random.randint(0, 65535, (512, 512), dtype=np.uint16)
            >>> normalized = converter.normalize_image(raw_data)
            >>> print(normalized.dtype, normalized.min(), normalized.max())
            uint8 0 255
        """
        logger.info(f"Normalizing image: dtype={img_data.dtype}, shape={img_data.shape}")
        logger.info(f"Value range: min={img_data.min()}, max={img_data.max()}, mean={img_data.mean():.2f}")
        
        # If already uint8 with good contrast, return as-is
        if img_data.dtype == np.uint8:
            if img_data.max() > 200 and img_data.min() < 50:
                logger.info("Image already well-contrasted, skipping normalization")
                return img_data
        
        # Use percentiles to avoid outliers
        if self.conversion_settings['normalize_percentiles']:
            # Sample for large images to save memory
            if img_data.size > 10_000_000:
                logger.info("Large image detected, sampling for percentile calculation...")
                sample = img_data.ravel()[::100]
                p_low = np.percentile(sample, self.conversion_settings['percentile_low'])
                p_high = np.percentile(sample, self.conversion_settings['percentile_high'])
            else:
                p_low = np.percentile(img_data, self.conversion_settings['percentile_low'])
                p_high = np.percentile(img_data, self.conversion_settings['percentile_high'])
            
            logger.info(f"Percentiles: {self.conversion_settings['percentile_low']}%={p_low}, "
                       f"{self.conversion_settings['percentile_high']}%={p_high}")
        else:
            p_low = img_data.min()
            p_high = img_data.max()
        
        # Normalize
        if p_high - p_low > 0:
            # Use float32 to save memory
            img_normalized = img_data.astype(np.float32)
            np.clip(img_normalized, p_low, p_high, out=img_normalized)
            img_normalized -= p_low
            img_normalized *= (255.0 / (p_high - p_low))
            result = img_normalized.astype(np.uint8)
            
            logger.info(f"Normalized: min={result.min()}, max={result.max()}")
            return result
        else:
            logger.warning("No variation in image data")
            return np.zeros_like(img_data, dtype=np.uint8)
    
    def enhance_image(self, img_data: np.ndarray) -> np.ndarray:
        """
        Apply visual enhancements to image while preserving scientific data.
        
        Enhancements include:
        - CLAHE (Contrast Limited Adaptive Histogram Equalization)
        - Contrast adjustment
        - Sharpness adjustment
        
        Args:
            img_data (np.ndarray): Input image data (uint8)
            
        Returns:
            np.ndarray: Enhanced image data
            
        Example:
            >>> converter = ImageConverter()
            >>> img = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
            >>> enhanced = converter.enhance_image(img)
        """
        # Apply CLAHE if enabled
        if self.conversion_settings['use_clahe']:
            try:
                logger.info("Applying CLAHE enhancement...")
                clahe = cv2.createCLAHE(
                    clipLimit=self.conversion_settings['clahe_clip_limit'],
                    tileGridSize=self.conversion_settings['clahe_tile_grid_size']
                )
                
                if len(img_data.shape) == 2:
                    img_data = clahe.apply(img_data)
                else:
                    # Apply to each channel
                    for i in range(img_data.shape[2]):
                        img_data[:, :, i] = clahe.apply(img_data[:, :, i])
                
                logger.info("CLAHE applied successfully")
            except Exception as e:
                logger.warning(f"CLAHE failed: {e}, skipping")
        
        # Convert to PIL for additional enhancements
        if len(img_data.shape) == 2:
            img = Image.fromarray(img_data, 'L')
        else:
            img = Image.fromarray(img_data, 'RGB')
        
        # Enhance contrast
        if self.conversion_settings['enhance_contrast']:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.conversion_settings['contrast_factor'])
            logger.info(f"Contrast enhanced by factor {self.conversion_settings['contrast_factor']}")
        
        # Enhance sharpness
        if self.conversion_settings['enhance_sharpness']:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(self.conversion_settings['sharpness_factor'])
            logger.info(f"Sharpness enhanced by factor {self.conversion_settings['sharpness_factor']}")
        
        # Convert back to numpy array
        return np.array(img)
    
    def convert_to_pil(self, img_data: np.ndarray) -> Image.Image:
        """
        Convert numpy array to PIL Image.
        
        Args:
            img_data (np.ndarray): Image data
            
        Returns:
            PIL.Image: PIL Image object
        """
        if len(img_data.shape) == 2:
            return Image.fromarray(img_data, 'L')
        else:
            return Image.fromarray(img_data, 'RGB')
    
    def convert_with_vips(self, img_data: np.ndarray, output_path: Union[str, Path],
                          format: str = 'TIFF', max_dimension: Optional[int] = None) -> bool:
        """
        Convert image using VIPS for better performance on large images.
        
        Args:
            img_data (np.ndarray): Image data (uint8)
            output_path (Union[str, Path]): Output file path
            format (str): Output format
            max_dimension (Optional[int]): Maximum dimension for resizing
            
        Returns:
            bool: True if successful
        """
        if not self.vips_available:
            logger.warning("VIPS not available, cannot use convert_with_vips")
            return False
        
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create VIPS image from numpy array
            if len(img_data.shape) == 2:
                # Grayscale
                height, width = img_data.shape
                vips_img = self.pyvips.Image.new_from_memory(
                    img_data.tobytes(), width, height, 1, 'uchar'
                )
            else:
                # RGB
                height, width, bands = img_data.shape
                vips_img = self.pyvips.Image.new_from_memory(
                    img_data.tobytes(), width, height, bands, 'uchar'
                )
            
            # Resize if needed
            if max_dimension and max(vips_img.width, vips_img.height) > max_dimension:
                scale = max_dimension / max(vips_img.width, vips_img.height)
                logger.info(f"VIPS: Resizing from {vips_img.width}x{vips_img.height} (scale={scale:.3f})")
                vips_img = vips_img.resize(scale, kernel='lanczos3')
            
            # Save with appropriate settings
            format_upper = format.upper()
            if format_upper == 'TIFF':
                compression = self.conversion_settings.get('tiff_compression', 'tiff_lzw')
                if compression == 'tiff_deflate':
                    vips_img.write_to_file(str(output_path), compression='deflate')
                elif compression in ['lzw', 'tiff_lzw']:
                    vips_img.write_to_file(str(output_path), compression='lzw')
                else:
                    vips_img.write_to_file(str(output_path), compression='none')
            elif format_upper in ['JPEG', 'JPG']:
                quality = self.conversion_settings.get('jpeg_quality', 95)
                vips_img.write_to_file(str(output_path), Q=quality)
            elif format_upper == 'PNG':
                compression = self.conversion_settings.get('png_compression', 6)
                vips_img.write_to_file(str(output_path), compression=compression)
            elif format_upper == 'WEBP':
                quality = self.conversion_settings.get('webp_quality', 95)
                vips_img.write_to_file(str(output_path), Q=quality)
            else:
                logger.error(f"VIPS: Unsupported format {format}")
                return False
            
            logger.info(f"VIPS: Image saved successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"VIPS conversion error: {e}")
            return False
    
    def save_image(self, img: Image.Image, output_path: Union[str, Path], 
                   format: Optional[str] = None) -> bool:
        """
        Save PIL Image to file with appropriate settings.
        
        Args:
            img (PIL.Image): Image to save
            output_path (str or Path): Output file path
            format (str, optional): Output format ('PNG', 'JPEG', 'WEBP'). 
                                   Auto-detected from extension if None.
            
        Returns:
            bool: True if successful, False otherwise
            
        Example:
            >>> converter = ImageConverter()
            >>> img = Image.new('RGB', (100, 100))
            >>> converter.save_image(img, 'output.png', format='PNG')
            True
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect format from extension
        if format is None:
            format = output_path.suffix.upper().lstrip('.')
        
        format = format.upper()
        
        try:
            if format == 'PNG':
                img.save(
                    output_path, 
                    'PNG', 
                    optimize=True,
                    compress_level=self.conversion_settings['png_compression']
                )
            elif format in ['JPEG', 'JPG']:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(
                    output_path,
                    'JPEG',
                    quality=self.conversion_settings['jpeg_quality'],
                    optimize=True
                )
            elif format == 'WEBP':
                img.save(
                    output_path,
                    'WEBP',
                    quality=self.conversion_settings['webp_quality'],
                    method=6  # Best compression
                )
            elif format == 'TIFF':
                # Use LZW compression for TIFF
                compression = self.conversion_settings.get('tiff_compression', 'tiff_lzw')
                if compression == 'tiff_deflate':
                    img.save(output_path, 'TIFF', compression='tiff_deflate')
                elif compression == 'lzw':
                    img.save(output_path, 'TIFF', compression='tiff_lzw')
                else:
                    img.save(output_path, 'TIFF')
            else:
                logger.error(f"Unsupported format: {format}")
                return False
            
            logger.info(f"Image saved successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return False
    
    def convert_file(self, input_path: Union[str, Path], 
                     output_path: Union[str, Path],
                     format: Optional[str] = None,
                     enhance: bool = True,
                     max_dimension: Optional[int] = None) -> bool:
        """
        Convert a single .IMG file to standard image format.
        
        This is the main conversion function that orchestrates the entire process:
        1. Load PDS image
        2. Normalize data
        3. Enhance (optional)
        4. Save to output format
        
        Args:
            input_path (str or Path): Path to input .IMG file
            output_path (str or Path): Path to output image file
            format (str, optional): Output format. Auto-detected if None.
            enhance (bool): Whether to apply visual enhancements. Default True.
            max_dimension (int, optional): Maximum dimension for resizing. None = no resize.
            
        Returns:
            bool: True if successful, False otherwise
            
        Example:
            >>> converter = ImageConverter()
            >>> success = converter.convert_file(
            ...     'input/mars.img',
            ...     'output/mars.png',
            ...     format='PNG',
            ...     enhance=True
            ... )
            >>> print(success)
            True
        """
        logger.info(f"Converting {input_path} -> {output_path}")
        
        try:
            # Load image
            img_data = self.load_pds_image(input_path)
            if img_data is None:
                logger.error("Failed to load image")
                return False
            
            # Normalize
            img_data = self.normalize_image(img_data)
            
            # Enhance
            if enhance:
                img_data = self.enhance_image(img_data)
            
            # Determine if we should use VIPS for large images
            total_pixels = img_data.shape[0] * img_data.shape[1]
            vips_threshold = self.conversion_settings.get('vips_threshold_pixels', 10_000_000)
            use_vips = self.vips_available and total_pixels > vips_threshold
            
            if use_vips:
                logger.info(f"Using VIPS for large image ({total_pixels:,} pixels)")
                # Use VIPS for better performance
                success = self.convert_with_vips(img_data, output_path, format or 'TIFF', max_dimension)
                
                # Clean up
                del img_data
                gc.collect()
                
                return success
            else:
                # Use PIL for smaller images
                logger.info(f"Using PIL for image ({total_pixels:,} pixels)")
                
                # Convert to PIL
                img = self.convert_to_pil(img_data)
                
                # Resize if needed
                if max_dimension and max(img.size) > max_dimension:
                    logger.info(f"Resizing from {img.size} to fit {max_dimension}px")
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                # Clean up numpy array
                del img_data
                gc.collect()
                
                # Save
                success = self.save_image(img, output_path, format)
                
                # Clean up
                del img
                gc.collect()
                
                return success
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def convert_to_bytes(self, input_path: Union[str, Path],
                         format: str = 'PNG',
                         enhance: bool = True,
                         max_dimension: Optional[int] = None) -> Optional[BytesIO]:
        """
        Convert image to bytes (for web serving).
        
        Args:
            input_path (str or Path): Path to input .IMG file
            format (str): Output format ('PNG', 'JPEG', 'WEBP')
            enhance (bool): Whether to apply enhancements
            max_dimension (int, optional): Maximum dimension for resizing
            
        Returns:
            BytesIO or None: Image bytes, or None on error
            
        Example:
            >>> converter = ImageConverter()
            >>> img_bytes = converter.convert_to_bytes('input.img', format='PNG')
            >>> if img_bytes:
            ...     with open('output.png', 'wb') as f:
            ...         f.write(img_bytes.getvalue())
        """
        try:
            # Load and process
            img_data = self.load_pds_image(input_path)
            if img_data is None:
                return None
            
            img_data = self.normalize_image(img_data)
            
            if enhance:
                img_data = self.enhance_image(img_data)
            
            img = self.convert_to_pil(img_data)
            
            if max_dimension and max(img.size) > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Save to bytes
            img_io = BytesIO()
            
            if format.upper() == 'PNG':
                img.save(img_io, 'PNG', optimize=True, 
                        compress_level=self.conversion_settings['png_compression'])
            elif format.upper() in ['JPEG', 'JPG']:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(img_io, 'JPEG', 
                        quality=self.conversion_settings['jpeg_quality'],
                        optimize=True)
            elif format.upper() == 'WEBP':
                img.save(img_io, 'WEBP',
                        quality=self.conversion_settings['webp_quality'],
                        method=6)
            
            img_io.seek(0)
            
            # Cleanup
            del img_data, img
            gc.collect()
            
            return img_io
            
        except Exception as e:
            logger.error(f"Conversion to bytes failed: {e}")
            return None


# Convenience function for quick conversions
def convert_img_file(input_path: str, output_path: str, 
                     format: str = 'PNG', enhance: bool = True) -> bool:
    """
    Quick conversion function for single files.
    
    Args:
        input_path (str): Input .IMG file path
        output_path (str): Output image file path
        format (str): Output format ('PNG', 'JPEG', 'WEBP')
        enhance (bool): Apply visual enhancements
        
    Returns:
        bool: True if successful
        
    Example:
        >>> from simple_converter import convert_img_file
        >>> convert_img_file('mars.img', 'mars.png', format='PNG')
        True
    """
    converter = ImageConverter()
    return converter.convert_file(input_path, output_path, format, enhance)
