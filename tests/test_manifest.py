import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from core.manifest import (
    ManifestEntry,
    Manifest,
    save_manifest,
    load_manifest,
    make_manifest,
    sha256_file,
    prepare_backup_path,
)
from core.scanner import FileEntry


def test_manifest_save_load():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")
        
        # Create manifest entry
        entry = ManifestEntry(
            source=test_file,
            backup="files/test.txt",
            size=11,
            sha256=sha256_file(test_file),
            mtime=datetime.now().isoformat(),
        )
        
        manifest = Manifest(
            backup_date=datetime.now().isoformat(),
            machine="test",
            os="Linux",
            total_files=1,
            total_size=11,
            files=[entry],
        )
        
        save_manifest(manifest, temp_dir)
        loaded_manifest = load_manifest(temp_dir)
        
        assert loaded_manifest.total_files == 1
        assert loaded_manifest.total_size == 11
        assert loaded_manifest.files[0].source == test_file
