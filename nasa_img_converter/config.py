"""
Configuration Module for NASA Image Converter
==============================================

This module contains all configuration parameters for image processing,
conversion, and Deep Zoom tile generation.

Author: NASA Image Converter Team
License: MIT
"""

import os
from pathlib import Path
from typing import Dict, Any


class ProcessingConfig:
    """
    Configuration class for image processing parameters.
    
    Attributes:
        INPUT_DIR (Path): Directory containing input .IMG files
        OUTPUT_DIR (Path): Directory for processed output files
        CACHE_DIR (Path): Directory for caching processed images
        DZI_DIR (Path): Directory for Deep Zoom Image tiles
        TEMP_DIR (Path): Temporary directory for intermediate files
    """
    
    # Directory Configuration
    BASE_DIR = Path(__file__).parent
    INPUT_DIR = BASE_DIR / "input_images"
    OUTPUT_DIR = BASE_DIR / "output_images"
    CACHE_DIR = BASE_DIR / "cache"
    DZI_DIR = BASE_DIR / "dzi_tiles"
    TEMP_DIR = BASE_DIR / "temp_uploads"
    # Image Conversion Settings
    CONVERSION_SETTINGS = {
        # Output format settings
        'default_format': 'TIFF',  # TIFF for scientific accuracy, PNG, JPEG, WEBP
        'jpeg_quality': 95,
        'png_compression': 6,  # 0-9, higher = smaller file but slower
        'tiff_compression': 'tiff_deflate',  # None, 'tiff_deflate', 'jpeg', 'lzw'
        'webp_quality': 95,
        'enhance_contrast': True,
        'contrast_factor': 1.15,  # 1.0 = no change, >1.0 = more contrast
        'enhance_sharpness': True,
        'sharpness_factor': 1.1,  # 1.0 = no change, >1.0 = sharper
        'use_clahe': True,
        'clahe_clip_limit': 2.0,
        'clahe_tile_grid_size': (8, 8),
        
        # Normalization settings
        'normalize_percentiles': True,
        'percentile_low': 2,
        'percentile_high': 98,
        
        # VIPS settings for large image handling
        'use_vips': True,  # Use pyvips for large images (better performance)
        'vips_threshold_pixels': 10_000_000,  # Use VIPS for images > 10M pixels
        'vips_memory_limit_mb': 2000,  # Memory limit for VIPS operations
    }
    
    # Deep Zoom / Tile Generation Settings
    DEEPZOOM_SETTINGS = {
        # Tile size in pixels (256 is standard for OpenSeadragon)
        'tile_size': 256,
        
        # Overlap between tiles in pixels (1-2 recommended)
        'tile_overlap': 1,
        
        # Tile format
        'tile_format': 'jpg',  # 'jpg' or 'png'
        
        # JPEG quality for tiles
        'tile_quality': 85,
        
        # Minimum image size to trigger Deep Zoom (in pixels)
        # Images smaller than this will use standard viewing
        'min_size_for_deepzoom': 4096,
        
        # Maximum pyramid levels (None = auto-calculate)
        'max_levels': None,
        
        # Use VIPS for tile generation (faster, less memory)
        'use_vips': True,
        
        # Memory limit for VIPS (in MB)
        'vips_memory_limit': 2000,
    }
    
    # Batch Processing Settings
    BATCH_SETTINGS = {
        # Maximum concurrent processes
        'max_workers': 4,
        
        # Skip existing files
        'skip_existing': True,
        
        # Continue on error
        'continue_on_error': True,
        
        # Generate report after batch processing
        'generate_report': True,
        
        # Supported input extensions
        'input_extensions': ['.img', '.IMG', '.raw', '.RAW', '.fits', '.FITS'],
    }
    
    # Memory Management Settings
    MEMORY_SETTINGS = {
        # Maximum file size to load into memory (in MB)
        'max_memory_load': 500,
        
        # Use memory-mapped files for large images
        'use_memory_mapping': True,
        
        # Chunk size for streaming large files (in bytes)
        'chunk_size': 65536,  # 64KB
        
        # Enable garbage collection after each image
        'aggressive_gc': True,
        
        # Maximum dimension for preview images
        'max_preview_dimension': 4096,
    }
    
    # Error Handling Settings
    ERROR_SETTINGS = {
        # Log errors to file
        'log_errors': True,
        'error_log_file': BASE_DIR / 'error_log.txt',
        
        # Retry failed conversions
        'retry_on_failure': True,
        'max_retries': 2,
        
        # Fallback to alternative libraries on error
        'use_fallback_libraries': True,
    }
    
    # PDS Format Detection Settings
    PDS_SETTINGS = {
        # Bytes to read for format detection
        'detection_chunk_size': 10000,
        
        # Supported PDS versions
        'supported_versions': ['PDS3', 'PDS4'],
        
        # Libraries to try (in order)
        'library_priority': ['pdr', 'planetaryimage', 'gdal'],
    }
    
    # Web Server Settings
    WEB_SETTINGS = {
        # Maximum upload size (in MB)
        'max_upload_size': 500,
        
        # Cache timeout (in seconds)
        'cache_timeout': 3600,  # 1 hour
        
        # Enable CORS
        'enable_cors': True,
        
        # OpenSeadragon CDN version
        'openseadragon_version': '4.1.0',
    }
    
    @classmethod
    def create_directories(cls):
        """
        Create all necessary directories if they don't exist.
        
        Example:
            >>> ProcessingConfig.create_directories()
        """
        directories = [
            cls.INPUT_DIR,
            cls.OUTPUT_DIR,
            cls.CACHE_DIR,
            cls.DZI_DIR,
            cls.TEMP_DIR,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary.
        
        Returns:
            dict: Complete configuration dictionary
            
        Example:
            >>> config = ProcessingConfig.get_config_dict()
            >>> print(config['CONVERSION_SETTINGS']['default_format'])
            'PNG'
        """
        return {
            'CONVERSION_SETTINGS': cls.CONVERSION_SETTINGS,
            'DEEPZOOM_SETTINGS': cls.DEEPZOOM_SETTINGS,
            'BATCH_SETTINGS': cls.BATCH_SETTINGS,
            'MEMORY_SETTINGS': cls.MEMORY_SETTINGS,
            'ERROR_SETTINGS': cls.ERROR_SETTINGS,
            'PDS_SETTINGS': cls.PDS_SETTINGS,
            'WEB_SETTINGS': cls.WEB_SETTINGS,
        }
    
    @classmethod
    def update_setting(cls, category: str, key: str, value: Any):
        """
        Update a specific configuration setting.
        
        Args:
            category (str): Configuration category (e.g., 'CONVERSION_SETTINGS')
            key (str): Setting key to update
            value (Any): New value for the setting
            
        Example:
            >>> ProcessingConfig.update_setting('CONVERSION_SETTINGS', 'default_format', 'WEBP')
        """
        if hasattr(cls, category):
            settings = getattr(cls, category)
            if isinstance(settings, dict):
                settings[key] = value
            else:
                raise ValueError(f"{category} is not a dictionary")
        else:
            raise ValueError(f"Category {category} not found")


# Initialize directories on import
ProcessingConfig.create_directories()


# Export configuration instance
config = ProcessingConfig()
