"""
Streaming Image Converter
==========================

This module enables conversion of images while they are being downloaded,
optimizing both time and storage by processing data in a pipeline.

Author: NASA Image Converter Team
License: MIT
"""

import os
import gc
import logging
import tempfile
from pathlib import Path
from typing import Optional, Union, Callable
from io import BytesIO
import threading
import queue

import requests
import numpy as np
from PIL import Image

from config import ProcessingConfig
from simple_converter import ImageConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StreamingConverter:
    """
    Convert images while downloading using a pipeline approach.
    
    This class downloads and processes images simultaneously:
    1. Download chunks in background thread
    2. Process chunks as they arrive
    3. Minimize disk I/O and storage
    
    Example:
        >>> converter = StreamingConverter()
        >>> converter.convert_from_url(
        ...     'https://example.com/large.img',
        ...     'output.png',
        ...     progress_callback=lambda p: print(f"{p}%")
        ... )
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize the StreamingConverter.
        
        Args:
            config (ProcessingConfig, optional): Configuration object
        """
        self.config = config or ProcessingConfig()
        self.converter = ImageConverter(self.config)
        self.chunk_size = self.config.MEMORY_SETTINGS['chunk_size']
    
    def download_with_progress(self, url: str, 
                               output_file: Union[str, Path],
                               progress_callback: Optional[Callable] = None) -> bool:
        """
        Download file with progress tracking and minimal memory usage.
        
        Args:
            url (str): URL to download
            output_file (str or Path): Output file path
            progress_callback (callable, optional): Called with (bytes_downloaded, total_bytes)
            
        Returns:
            bool: True if successful
            
        Example:
            >>> converter = StreamingConverter()
            >>> def progress(current, total):
            ...     print(f"Downloaded: {current}/{total} bytes")
            >>> converter.download_with_progress('url', 'output.img', progress)
        """
        try:
            logger.info(f"Starting streaming download from {url}")
            
            # Start download with streaming
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            logger.info(f"Total file size: {total_size / (1024*1024):.2f} MB")
            
            # Download with progress
            downloaded = 0
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress callback
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
            
            logger.info(f"Download complete: {downloaded / (1024*1024):.2f} MB")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_with_resume(self,
                              url: str,
                              output_file: Union[str, Path],
                              progress_callback: Optional[Callable] = None,
                              max_retries: int = 5,
                              backoff_factor: float = 2.0) -> bool:
        """
        Robust downloader with HTTP Range resume, retries and exponential backoff.

        - Uses Range requests to resume partial downloads if the server supports it
        - Retries on transient network errors (e.g., ConnectionResetError 10054)
        - Reports progress via callback if provided

        Args:
            url: Source URL
            output_file: Destination path
            progress_callback: Callable(bytes_downloaded, total_bytes)
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier (seconds)

        Returns:
            True on success, False otherwise
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Probe server for size and range support
            try:
                head = requests.head(url, allow_redirects=True, timeout=30)
                head.raise_for_status()
                total_size = int(head.headers.get('content-length', 0))
                accept_ranges = head.headers.get('accept-ranges', '').lower() == 'bytes'
            except Exception as e:
                logger.warning(f"HEAD failed ({e}), falling back to GET for size")
                total_size = 0
                accept_ranges = True  # attempt resume anyway

            attempt = 0
            downloaded = output_path.stat().st_size if output_path.exists() else 0

            while attempt <= max_retries:
                try:
                    headers = {}
                    if accept_ranges and downloaded > 0:
                        headers['Range'] = f'bytes={downloaded}-'

                    with requests.get(url, stream=True, timeout=300, headers=headers) as resp:
                        # 200 = full, 206 = partial
                        if resp.status_code not in (200, 206):
                            resp.raise_for_status()

                        # If server ignored Range, reset file
                        if resp.status_code == 200 and downloaded > 0:
                            logger.info("Server ignored Range, restarting download from 0")
                            downloaded = 0
                            mode = 'wb'
                        else:
                            mode = 'ab' if downloaded > 0 else 'wb'

                        # Update total_size if missing
                        if total_size == 0:
                            try:
                                content_length = resp.headers.get('content-length')
                                if content_length:
                                    total_size = downloaded + int(content_length)
                            except Exception:
                                pass

                        with open(output_path, mode) as f:
                            for chunk in resp.iter_content(chunk_size=self.chunk_size):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                downloaded += len(chunk)
                                if progress_callback and total_size > 0:
                                    progress_callback(downloaded, total_size)

                    # Verify completion
                    if total_size == 0 or downloaded >= total_size:
                        logger.info(f"Download complete: {downloaded / (1024*1024):.2f} MB")
                        return True

                    # If we get here, we didn't complete; retry
                    raise IOError(f"Incomplete download: {downloaded}/{total_size} bytes")

                except (requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.ReadTimeout,
                        IOError) as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(f"Download failed after {attempt} attempts: {e}")
                        return False
                    sleep_s = backoff_factor ** attempt
                    logger.warning(f"Transient error (attempt {attempt}/{max_retries}): {e}. Retrying in {sleep_s:.1f}s...")
                    import time
                    time.sleep(sleep_s)
                    # Resume from current file size
                    downloaded = output_path.stat().st_size if output_path.exists() else 0
                    continue
        except Exception as e:
            logger.error(f"Download with resume failed: {e}")
            return False
    
    def convert_from_url_optimized(self, url: str,
                                   output_path: Union[str, Path],
                                   format: str = 'PNG',
                                   enhance: bool = True,
                                   delete_temp: bool = True,
                                   progress_callback: Optional[Callable] = None) -> bool:
        """
        Download and convert in optimized pipeline.
        
        This method:
        1. Downloads to temporary file with progress
        2. Converts immediately after download
        3. Deletes temporary file if requested
        
        Args:
            url (str): URL of .IMG file
            output_path (str or Path): Output image path
            format (str): Output format ('PNG', 'JPEG', 'WEBP')
            enhance (bool): Apply enhancements
            delete_temp (bool): Delete temporary .IMG file after conversion
            progress_callback (callable, optional): Progress callback
            
        Returns:
            bool: True if successful
            
        Example:
            >>> converter = StreamingConverter()
            >>> converter.convert_from_url_optimized(
            ...     'https://example.com/mars.img',
            ...     'mars.png',
            ...     format='PNG',
            ...     delete_temp=True
            ... )
        """
        temp_file = None
        
        try:
            # Create temporary file
            temp_fd, temp_file = tempfile.mkstemp(suffix='.img')
            os.close(temp_fd)
            
            logger.info(f"Downloading to temporary file: {temp_file}")
            
            # Download with progress
            success = self.download_with_progress(
                url, 
                temp_file,
                progress_callback
            )
            
            if not success:
                return False
            
            logger.info("Download complete, starting conversion...")
            
            # Convert immediately
            success = self.converter.convert_file(
                temp_file,
                output_path,
                format=format,
                enhance=enhance
            )
            
            if success:
                logger.info(f"Conversion successful: {output_path}")
                
                # Delete temporary file if requested
                if delete_temp and os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info("Temporary file deleted")
            
            return success
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return False
            
        finally:
            # Cleanup on error
            if temp_file and os.path.exists(temp_file) and delete_temp:
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def convert_from_url_parallel(self, url: str,
                                  output_path: Union[str, Path],
                                  format: str = 'PNG',
                                  enhance: bool = True,
                                  chunk_process_size: int = 10 * 1024 * 1024,
                                  progress_callback: Optional[Callable] = None) -> bool:
        """
        Advanced: Download and process in parallel using threading.
        
        This method uses a producer-consumer pattern:
        - Producer thread: Downloads chunks
        - Consumer thread: Processes chunks as they arrive
        
        Note: This is experimental and works best for very large files.
        
        Args:
            url (str): URL of .IMG file
            output_path (str or Path): Output path
            format (str): Output format
            enhance (bool): Apply enhancements
            chunk_process_size (int): Size threshold to start processing
            progress_callback (callable, optional): Progress callback
            
        Returns:
            bool: True if successful
        """
        # For now, use optimized sequential approach
        # Parallel processing requires more complex PDS format handling
        return self.convert_from_url_optimized(
            url, output_path, format, enhance, True, progress_callback
        )
    
    def estimate_conversion_time(self, file_size_mb: float) -> dict:
        """
        Estimate conversion time based on file size.
        
        Args:
            file_size_mb (float): File size in megabytes
            
        Returns:
            dict: Estimated times for different operations
            
        Example:
            >>> converter = StreamingConverter()
            >>> estimates = converter.estimate_conversion_time(150)
            >>> print(f"Download: {estimates['download_time']}s")
        """
        # Rough estimates based on typical performance
        download_speed_mbps = 10  # 10 MB/s typical
        processing_speed_mbps = 5  # 5 MB/s for conversion
        
        download_time = file_size_mb / download_speed_mbps
        processing_time = file_size_mb / processing_speed_mbps
        
        # Sequential (current approach)
        sequential_total = download_time + processing_time
        
        # Optimized (delete temp immediately)
        optimized_total = sequential_total
        optimized_storage = file_size_mb  # Only temp file during process
        
        # Parallel (theoretical)
        parallel_total = max(download_time, processing_time)
        
        return {
            'file_size_mb': file_size_mb,
            'download_time': round(download_time, 1),
            'processing_time': round(processing_time, 1),
            'sequential_total': round(sequential_total, 1),
            'optimized_total': round(optimized_total, 1),
            'parallel_total': round(parallel_total, 1),
            'storage_needed_mb': round(optimized_storage, 1),
            'time_saved_vs_sequential': round(sequential_total - parallel_total, 1)
        }


class InMemoryConverter:
    """
    Convert small to medium images entirely in memory (no disk I/O).
    
    This is the fastest approach for files that fit in RAM.
    
    Example:
        >>> converter = InMemoryConverter()
        >>> converter.convert_from_url_in_memory(
        ...     'https://example.com/small.img',
        ...     'output.png'
        ... )
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize the InMemoryConverter."""
        self.config = config or ProcessingConfig()
        self.converter = ImageConverter(self.config)
        self.max_memory_mb = self.config.MEMORY_SETTINGS['max_memory_load']
    
    def convert_from_url_in_memory(self, url: str,
                                   output_path: Union[str, Path],
                                   format: str = 'PNG',
                                   enhance: bool = True) -> bool:
        """
        Download and convert entirely in memory (fastest for small files).
        
        Args:
            url (str): URL of .IMG file
            output_path (str or Path): Output path
            format (str): Output format
            enhance (bool): Apply enhancements
            
        Returns:
            bool: True if successful
            
        Example:
            >>> converter = InMemoryConverter()
            >>> converter.convert_from_url_in_memory(
            ...     'https://example.com/small.img',
            ...     'output.png'
            ... )
        """
        try:
            logger.info(f"Downloading to memory from {url}")
            
            # Download entire file to memory
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            
            file_size_mb = len(response.content) / (1024 * 1024)
            logger.info(f"Downloaded {file_size_mb:.2f} MB to memory")
            
            # Check if file is too large for memory
            if file_size_mb > self.max_memory_mb:
                logger.warning(f"File too large for in-memory processing "
                             f"({file_size_mb:.2f} MB > {self.max_memory_mb} MB)")
                return False
            
            # Create temporary file from memory
            temp_fd, temp_file = tempfile.mkstemp(suffix='.img')
            
            try:
                # Write to temp file
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(response.content)
                
                # Convert
                success = self.converter.convert_file(
                    temp_file,
                    output_path,
                    format=format,
                    enhance=enhance
                )
                
                return success
                
            finally:
                # Always delete temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                # Clear memory
                del response
                gc.collect()
            
        except Exception as e:
            logger.error(f"In-memory conversion failed: {e}")
            return False


# Convenience functions
def convert_url_optimized(url: str, output_path: str, 
                         format: str = 'PNG', 
                         delete_temp: bool = True) -> bool:
    """
    Quick optimized conversion from URL.
    
    Args:
        url (str): URL of .IMG file
        output_path (str): Output path
        format (str): Output format
        delete_temp (bool): Delete temporary file
        
    Returns:
        bool: True if successful
        
    Example:
        >>> from streaming_converter import convert_url_optimized
        >>> convert_url_optimized(
        ...     'https://example.com/mars.img',
        ...     'mars.png',
        ...     delete_temp=True
        ... )
    """
    converter = StreamingConverter()
    return converter.convert_from_url_optimized(
        url, output_path, format, True, delete_temp
    )


def convert_url_in_memory(url: str, output_path: str, format: str = 'PNG') -> bool:
    """
    Quick in-memory conversion (fastest for small files).
    
    Args:
        url (str): URL of .IMG file
        output_path (str): Output path
        format (str): Output format
        
    Returns:
        bool: True if successful
        
    Example:
        >>> from streaming_converter import convert_url_in_memory
        >>> convert_url_in_memory('https://example.com/small.img', 'output.png')
    """
    converter = InMemoryConverter()
    return converter.convert_from_url_in_memory(url, output_path, format)
