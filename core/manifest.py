import os
import json
import hashlib
import platform
import socket
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict

from core.compression import decompress_zip


def prepare_backup_path(backup_path: str) -> tuple[str, Optional[str]]:
    """
    Prepare backup path: if it's a zip file, extract it and return the actual directory
    and the temp directory to clean up later.
    """
    temp_dir = None
    actual_dir = backup_path

    if backup_path.endswith(".zip") and os.path.isfile(backup_path):
        temp_dir = tempfile.mkdtemp()
        decompress_zip(backup_path, temp_dir)
        extracted_items = os.listdir(temp_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
            actual_dir = os.path.join(temp_dir, extracted_items[0])
        else:
            actual_dir = temp_dir

    return actual_dir, temp_dir


@dataclass
class ManifestEntry:
    source: str
    backup: str
    size: int
    sha256: str
    mtime: str


@dataclass
class Manifest:
    backup_date: str
    machine: str
    os: str
    total_files: int
    total_size: int
    files: List[ManifestEntry]
    user: str = ""
    original_profile: str = ""
    backup_type: str = "full"  # "full" or "incremental"
    previous_backup_dir: str = ""


def sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def _safe_backup_name(source_path: str, sha256: str) -> str:
    basename = Path(source_path).name
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in basename)
    return f"{sha256[:8]}_{safe}"


def build_manifest_entry(source_path: str, backup_relative: str) -> Optional[ManifestEntry]:
    try:
        stat = os.stat(source_path)
        sha = sha256_file(source_path)
        if sha is None:
            return None
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return ManifestEntry(
            source=source_path,
            backup=backup_relative,
            size=stat.st_size,
            sha256=sha,
            mtime=mtime,
        )
    except OSError:
        return None


def save_manifest(manifest: Manifest, backup_dir: str) -> str:
    path = os.path.join(backup_dir, "manifest.json")
    data = {
        "user": manifest.user,
        "original_profile": manifest.original_profile,
        "backup_date": manifest.backup_date,
        "machine": manifest.machine,
        "os": manifest.os,
        "total_files": manifest.total_files,
        "total_size": manifest.total_size,
        "files": [asdict(e) for e in manifest.files],
        "backup_type": manifest.backup_type,
        "previous_backup_dir": manifest.previous_backup_dir,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_manifest(backup_dir: str) -> Manifest:
    actual_dir, temp_dir = prepare_backup_path(backup_dir)
    try:
        path = os.path.join(actual_dir, "manifest.json")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"manifest.json não encontrado em: {backup_dir}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = [ManifestEntry(**e) for e in data.get("files", [])]
        manifest = Manifest(
            backup_date=data.get("backup_date", ""),
            machine=data.get("machine", ""),
            os=data.get("os", ""),
            total_files=data.get("total_files", len(entries)),
            total_size=data.get("total_size", 0),
            files=entries,
            user=data.get("user", ""),
            original_profile=data.get("original_profile", ""),
            backup_type=data.get("backup_type", "full"),
            previous_backup_dir=data.get("previous_backup_dir", ""),
        )
        return manifest
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def get_users_from_manifest(manifest: Manifest) -> List[str]:
    """Extract unique usernames from manifest entries."""
    users = set()
    for entry in manifest.files:
        path = Path(entry.source)
        if platform.system() == "Windows":
            # Windows: C:\Users\username\...
            if len(path.parts) >= 3 and path.parts[1].lower() == "users":
                users.add(path.parts[2])
        else:
            # Linux/macOS: /home/username/...
            if len(path.parts) >= 3 and path.parts[1] == "home":
                users.add(path.parts[2])
    return sorted(list(users))


def make_manifest(
    entries_with_sha: List[ManifestEntry],
    user: str = "",
    original_profile: str = "",
    backup_type: str = "full",
    previous_backup_dir: str = "",
) -> Manifest:
    return Manifest(
        backup_date=datetime.now().isoformat(),
        machine=socket.gethostname(),
        os=platform.system(),
        total_files=len(entries_with_sha),
        total_size=sum(e.size for e in entries_with_sha),
        files=entries_with_sha,
        user=user,
        original_profile=original_profile,
        backup_type=backup_type,
        previous_backup_dir=previous_backup_dir,
    )
