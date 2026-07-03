import os
import zipfile
from pathlib import Path
from typing import Optional, Callable
from enum import Enum


class CompressionLevel(Enum):
    NONE = 0
    STANDARD = 1
    DEFLATE = 2
    MAXIMUM = 9


def get_zip_compression_method(level: CompressionLevel) -> int:
    if level == CompressionLevel.NONE:
        return zipfile.ZIP_STORED
    elif level in (CompressionLevel.STANDARD, CompressionLevel.DEFLATE, CompressionLevel.MAXIMUM):
        return zipfile.ZIP_DEFLATED
    return zipfile.ZIP_STORED


def compress_directory(
    source_dir: str,
    output_zip: str,
    level: CompressionLevel = CompressionLevel.DEFLATE,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[int, int]:
    """
    Compress a directory into a ZIP file.
    
    Args:
        source_dir: Directory to compress
        output_zip: Path to output ZIP file
        level: Compression level
        progress_callback: Callback for progress (current, total, path)
    
    Returns:
        Tuple of (original_size_bytes, compressed_size_bytes)
    """
    source_path = Path(source_dir)
    original_size = 0
    file_list = []

    # Collect all files and calculate original size
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = Path(root) / file
            original_size += file_path.stat().st_size
            file_list.append(file_path)

    total_files = len(file_list)
    current = 0

    compression_method = get_zip_compression_method(level)
    compresslevel = level.value if level != CompressionLevel.NONE else None

    with zipfile.ZipFile(
        output_zip,
        'w',
        compression=compression_method,
        compresslevel=compresslevel
    ) as zipf:
        for file_path in file_list:
            arcname = file_path.relative_to(source_path)
            zipf.write(file_path, arcname)
            current += 1
            if progress_callback:
                progress_callback(current, total_files, str(file_path))

    compressed_size = Path(output_zip).stat().st_size
    return original_size, compressed_size


def decompress_zip(
    zip_path: str,
    extract_dir: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> None:
    """
    Decompress a ZIP file.
    
    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract to
        progress_callback: Callback for progress (current, total, path)
    """
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        file_list = zipf.infolist()
        total_files = len(file_list)
        for i, info in enumerate(file_list):
            zipf.extract(info, extract_dir)
            if progress_callback:
                progress_callback(i + 1, total_files, info.filename)
