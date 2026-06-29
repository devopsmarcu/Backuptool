import os
import hashlib
from dataclasses import dataclass
from typing import List, Callable, Optional


@dataclass
class FileEntry:
    path: str
    size: int
    mtime: float
    relative_path: str


def should_exclude(path: str, exclusions: List[str], excluded_extensions: List[str]) -> bool:
    norm = path.replace("\\", "/")
    for excl in exclusions:
        excl_norm = excl.replace("\\", "/")
        if excl_norm in norm:
            return True
    _, ext = os.path.splitext(path)
    if ext.lower() in [e.lower() for e in excluded_extensions]:
        return True
    return False


def scan_paths(
    paths: List[str],
    exclusions: List[str],
    excluded_extensions: List[str],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[FileEntry]:
    entries = []
    for base_path in paths:
        if not os.path.exists(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            # Filtrar diretórios excluídos in-place
            dirs[:] = [
                d for d in dirs
                if not should_exclude(os.path.join(root, d), exclusions, [])
            ]
            for filename in files:
                full_path = os.path.join(root, filename)
                if should_exclude(full_path, exclusions, excluded_extensions):
                    continue
                try:
                    stat = os.stat(full_path)
                    rel = os.path.relpath(full_path, os.path.dirname(base_path))
                    entries.append(FileEntry(
                        path=full_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        relative_path=rel,
                    ))
                    if progress_callback:
                        progress_callback(full_path)
                except (PermissionError, OSError):
                    continue
    return entries


def scan_profile_path(
    profile_path: str,
    exclusions: List[str],
    excluded_extensions: List[str],
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[FileEntry]:
    entries = []
    if not os.path.exists(profile_path):
        return entries
    for root, dirs, files in os.walk(profile_path):
        dirs[:] = [
            d for d in dirs
            if not should_exclude(os.path.join(root, d), exclusions, [])
        ]
        for filename in files:
            full_path = os.path.join(root, filename)
            if should_exclude(full_path, exclusions, excluded_extensions):
                continue
            try:
                stat = os.stat(full_path)
                rel = os.path.relpath(full_path, profile_path)
                entries.append(FileEntry(
                    path=full_path,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    relative_path=rel,
                ))
                if progress_callback:
                    progress_callback(full_path)
            except (PermissionError, OSError):
                continue
    return entries


def calculate_hash(path: str) -> Optional[str]:
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def total_size(entries: List[FileEntry]) -> int:
    return sum(e.size for e in entries)
