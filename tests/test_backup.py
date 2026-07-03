import os
import tempfile
import shutil
from datetime import datetime

from core.backup import (
    run_backup,
    find_latest_backup,
    list_backups,
    CompressionLevel,
)
from core.scanner import FileEntry
from core.manifest import load_manifest


def test_full_backup():
    with tempfile.TemporaryDirectory() as temp_dir:
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir)
        dest_dir = os.path.join(temp_dir, "dest")
        os.makedirs(dest_dir)
        
        # Create test files
        test_file1 = os.path.join(src_dir, "test1.txt")
        with open(test_file1, "w") as f:
            f.write("Test file 1")
        
        test_file2 = os.path.join(src_dir, "test2.txt")
        with open(test_file2, "w") as f:
            f.write("Test file 2")
        
        # Create FileEntry list
        entries = [
            FileEntry(
                path=test_file1,
                size=11,
                mtime=datetime.now().timestamp(),
                relative_path="test1.txt",
            ),
            FileEntry(
                path=test_file2,
                size=11,
                mtime=datetime.now().timestamp(),
                relative_path="test2.txt",
            ),
        ]
        
        result = run_backup(
            entries=entries,
            destination=dest_dir,
            backup_type="full",
            compression_level=CompressionLevel.NONE,
        )
        
        assert result.copied == 2
        assert result.errors == 0
        assert os.path.exists(result.backup_dir)
        
        # Check manifest
        manifest = load_manifest(result.backup_dir)
        assert manifest.total_files == 2
        assert manifest.backup_type == "full"


def test_list_backups():
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_dir = os.path.join(temp_dir, "dest")
        os.makedirs(dest_dir)
        
        # First backup
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Test content")
        
        entries = [
            FileEntry(
                path=test_file,
                size=12,
                mtime=datetime.now().timestamp(),
                relative_path="test.txt",
            ),
        ]
        
        run_backup(entries=entries, destination=dest_dir)
        run_backup(entries=entries, destination=dest_dir)
        
        backups = list_backups(dest_dir)
        assert len(backups) == 2
