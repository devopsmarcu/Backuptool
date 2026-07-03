import os
import tempfile
import shutil
from pathlib import Path

from core.compression import CompressionLevel, compress_directory, decompress_zip


def test_compression():
    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir)
        
        # Create test file
        test_file = os.path.join(src_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello World! " * 1000)
        
        # Test compress
        zip_path = os.path.join(temp_dir, "test.zip")
        original_size, compressed_size = compress_directory(
            src_dir,
            zip_path,
            CompressionLevel.DEFLATE,
        )
        
        assert os.path.exists(zip_path)
        assert original_size > 0
        assert compressed_size > 0
        
        # Test decompress
        dest_dir = os.path.join(temp_dir, "dest")
        decompress_zip(zip_path, dest_dir)
        
        assert os.path.exists(os.path.join(dest_dir, "test.txt"))
        with open(os.path.join(dest_dir, "test.txt"), "r") as f:
            content = f.read()
            assert content == "Hello World! " * 1000
