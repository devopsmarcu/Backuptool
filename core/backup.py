import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Callable, Optional, Dict

from core.scanner import FileEntry
from core.manifest import (
    ManifestEntry, Manifest,
    build_manifest_entry, make_manifest, save_manifest, load_manifest,
    sha256_file, _safe_backup_name,
)
from core.profiles import UserProfile
from core.compression import CompressionLevel, compress_directory


@dataclass
class IncrementalResult:
    """Result of incremental backup analysis."""
    new_files: List[FileEntry] = field(default_factory=list)
    modified_files: List[FileEntry] = field(default_factory=list)
    unchanged_files: List[FileEntry] = field(default_factory=list)
    previous_manifest: Optional[Manifest] = None


@dataclass
class BackupResult:
    copied: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: List[dict] = field(default_factory=list)
    backup_dir: str = ""
    manifest_path: str = ""
    user: str = ""
    original_profile: str = ""
    backup_type: str = "full"
    new_files: int = 0
    modified_files: int = 0
    unchanged_files: int = 0
    compression_level: CompressionLevel = CompressionLevel.NONE
    original_size: int = 0
    compressed_size: int = 0
    compressed_path: str = ""


def run_backup(
    entries: List[FileEntry],
    destination: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    backup_type: str = "full",
    previous_backup_dir: Optional[str] = None,
    compression_level: CompressionLevel = CompressionLevel.NONE,
) -> BackupResult:
    result = BackupResult(backup_type=backup_type, compression_level=compression_level)
    total = len(entries)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir = os.path.join(destination, f"Backup_{ts}")
    files_dir = os.path.join(backup_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    result.backup_dir = backup_dir

    # Determine which files to process
    files_to_process = entries
    if backup_type == "incremental" and previous_backup_dir:
        analysis = analyze_incremental(entries, previous_backup_dir)
        result.new_files = len(analysis.new_files)
        result.modified_files = len(analysis.modified_files)
        result.unchanged_files = len(analysis.unchanged_files)
        files_to_process = analysis.new_files + analysis.modified_files
    else:
        result.new_files = len(entries)
        result.modified_files = 0
        result.unchanged_files = 0

    manifest_entries: List[ManifestEntry] = []

    for i, entry in enumerate(files_to_process):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(i + 1, len(files_to_process), entry.path)

        sha = sha256_file(entry.path)
        if sha is None:
            result.errors += 1
            result.error_details.append({
                "file": entry.path,
                "error": "Não foi possível calcular hash (sem permissão ou arquivo bloqueado)",
            })
            continue

        dest_filename = _safe_backup_name(entry.path, sha)
        dest_path = os.path.join(files_dir, dest_filename)
        backup_relative = os.path.join("files", dest_filename)

        try:
            shutil.copy2(entry.path, dest_path)
            result.copied += 1
            m_entry = ManifestEntry(
                source=entry.path,
                backup=backup_relative,
                size=entry.size,
                sha256=sha,
                mtime=datetime.fromtimestamp(entry.mtime).isoformat(),
            )
            manifest_entries.append(m_entry)

        except PermissionError as e:
            result.errors += 1
            result.error_details.append({"file": entry.path, "error": f"Sem permissão: {e}"})
        except OSError as e:
            result.errors += 1
            result.error_details.append({"file": entry.path, "error": str(e)})

    if manifest_entries:
        manifest = make_manifest(
            manifest_entries,
            backup_type=backup_type,
            previous_backup_dir=previous_backup_dir or ""
        )
        result.manifest_path = save_manifest(manifest, backup_dir)

    # Compress the backup if requested
    if compression_level != CompressionLevel.NONE:
        zip_path = os.path.join(destination, f"Backup_{ts}.zip")
        
        def compression_progress(current: int, total: int, path: str):
            if on_progress:
                # Report compression progress as "Compressing: file X/Y"
                pass  # We'll handle this in the UI if needed
        
        original_size, compressed_size = compress_directory(
            backup_dir,
            zip_path,
            compression_level,
            compression_progress
        )
        result.original_size = original_size
        result.compressed_size = compressed_size
        result.compressed_path = zip_path

    return result


def find_latest_backup(destination: str) -> Optional[str]:
    """Find the latest backup directory in the destination."""
    if not os.path.exists(destination):
        return None
    backup_dirs = []
    for item in os.listdir(destination):
        item_path = os.path.join(destination, item)
        if os.path.isdir(item_path) and item.startswith("Backup_"):
            # Check if it has a manifest.json
            if os.path.exists(os.path.join(item_path, "manifest.json")):
                backup_dirs.append(item_path)
            # Check for multi-user backup (usuarios directory)
            elif os.path.exists(os.path.join(item_path, "usuarios")):
                backup_dirs.append(item_path)
    if not backup_dirs:
        return None
    # Sort by modification time (newest first)
    backup_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return backup_dirs[0]


def list_backups(destination: str) -> List[dict]:
    """List all backups in the destination with metadata."""
    if not os.path.exists(destination):
        return []
    backups = []
    for item in os.listdir(destination):
        item_path = os.path.join(destination, item)
        if os.path.isdir(item_path) and item.startswith("Backup_"):
            # Try to load manifest
            manifest_path = os.path.join(item_path, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    manifest = load_manifest(item_path)
                    backups.append({
                        "path": item_path,
                        "date": manifest.backup_date,
                        "machine": manifest.machine,
                        "os": manifest.os,
                        "total_files": manifest.total_files,
                        "total_size": manifest.total_size,
                        "type": manifest.backup_type,
                        "user": manifest.user,
                    })
                except Exception as e:
                    print(f"Error loading manifest from {item_path}: {e}")
            # Check for multi-user backup
            elif os.path.exists(os.path.join(item_path, "usuarios")):
                # Try to get first user's manifest
                users_dir = os.path.join(item_path, "usuarios")
                users = os.listdir(users_dir)
                if users:
                    first_user_dir = os.path.join(users_dir, users[0])
                    first_manifest_path = os.path.join(first_user_dir, "manifest.json")
                    if os.path.exists(first_manifest_path):
                        try:
                            manifest = load_manifest(first_user_dir)
                            backups.append({
                                "path": item_path,
                                "date": manifest.backup_date,
                                "machine": manifest.machine,
                                "os": manifest.os,
                                "type": manifest.backup_type,
                                "multi_user": True,
                            })
                        except Exception as e:
                            print(f"Error loading manifest from {first_manifest_path}: {e}")
    # Sort by date descending
    backups.sort(key=lambda x: x["date"], reverse=True)
    return backups


def analyze_incremental(
    entries: List[FileEntry],
    previous_backup_dir: str,
    user: Optional[str] = None
) -> IncrementalResult:
    """
    Analyze which files are new, modified, or unchanged compared to previous backup.
    """
    result = IncrementalResult()
    try:
        # Try to load previous manifest
        manifest_path = previous_backup_dir
        if user and os.path.exists(os.path.join(previous_backup_dir, "usuarios")):
            # Multi-user backup, look for user's manifest
            user_dir = os.path.join(previous_backup_dir, "usuarios", user)
            if os.path.exists(os.path.join(user_dir, "manifest.json")):
                manifest_path = user_dir
        result.previous_manifest = load_manifest(manifest_path)
    except Exception:
        # If no previous manifest found, treat as full backup
        result.new_files = entries.copy()
        return result

    # Create a dict for quick lookup of previous files by source path
    previous_files = {
        entry.source: entry
        for entry in result.previous_manifest.files
    }

    for entry in entries:
        if entry.path not in previous_files:
            result.new_files.append(entry)
        else:
            prev_entry = previous_files[entry.path]
            # Check if file is modified (size or mtime changed)
            if entry.size != prev_entry.size or entry.mtime != datetime.fromisoformat(prev_entry.mtime).timestamp():
                # To be safe, we should check SHA-256 as well, but let's do that
                # only if size or mtime changed to save time
                current_sha = sha256_file(entry.path)
                if current_sha != prev_entry.sha256:
                    result.modified_files.append(entry)
                else:
                    result.unchanged_files.append(entry)
            else:
                result.unchanged_files.append(entry)
    return result


@dataclass
class MultiUserBackupResult:
    backup_dir: str = ""
    copied: int = 0
    skipped: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    user_results: List[BackupResult] = field(default_factory=list)
    error_details: List[dict] = field(default_factory=list)
    compression_level: CompressionLevel = CompressionLevel.NONE
    original_size: int = 0
    compressed_size: int = 0
    compressed_path: str = ""


def run_user_backup(
    entries: List[FileEntry],
    user: str,
    original_profile: str,
    user_backup_dir: str,
    on_progress: Optional[Callable[[str, int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    backup_type: str = "full",
    previous_backup_dir: Optional[str] = None,
) -> BackupResult:
    result = BackupResult(user=user, original_profile=original_profile, backup_type=backup_type)
    total = len(entries)
    files_dir = os.path.join(user_backup_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    result.backup_dir = user_backup_dir

    # Determine which files to process
    files_to_process = entries
    if backup_type == "incremental" and previous_backup_dir:
        analysis = analyze_incremental(entries, previous_backup_dir, user=user)
        result.new_files = len(analysis.new_files)
        result.modified_files = len(analysis.modified_files)
        result.unchanged_files = len(analysis.unchanged_files)
        files_to_process = analysis.new_files + analysis.modified_files
    else:
        result.new_files = len(entries)
        result.modified_files = 0
        result.unchanged_files = 0

    manifest_entries: List[ManifestEntry] = []

    for i, entry in enumerate(files_to_process):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(user, i + 1, len(files_to_process), entry.path)

        sha = sha256_file(entry.path)
        if sha is None:
            result.errors += 1
            result.error_details.append({
                "user": user,
                "file": entry.path,
                "error": "Não foi possível calcular hash (sem permissão ou arquivo bloqueado)",
            })
            continue

        dest_filename = _safe_backup_name(entry.path, sha)
        dest_path = os.path.join(files_dir, dest_filename)
        backup_relative = os.path.join("files", dest_filename)

        try:
            shutil.copy2(entry.path, dest_path)
            result.copied += 1
            manifest_entries.append(ManifestEntry(
                source=entry.path,
                backup=backup_relative,
                size=entry.size,
                sha256=sha,
                mtime=datetime.fromtimestamp(entry.mtime).isoformat(),
            ))
        except PermissionError as e:
            result.errors += 1
            result.error_details.append({"user": user, "file": entry.path, "error": f"Sem permissão: {e}"})
        except OSError as e:
            result.errors += 1
            result.error_details.append({"user": user, "file": entry.path, "error": str(e)})

    manifest = make_manifest(
        manifest_entries,
        user=user,
        original_profile=original_profile,
        backup_type=backup_type,
        previous_backup_dir=previous_backup_dir or ""
    )
    result.manifest_path = save_manifest(manifest, user_backup_dir)
    return result


def run_user_backup(
    entries: List[FileEntry],
    user: str,
    original_profile: str,
    user_backup_dir: str,
    on_progress: Optional[Callable[[str, int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    backup_type: str = "full",
    previous_backup_dir: Optional[str] = None,
) -> BackupResult:
    result = BackupResult(user=user, original_profile=original_profile, backup_type=backup_type)
    total = len(entries)
    files_dir = os.path.join(user_backup_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    result.backup_dir = user_backup_dir

    # Determine which files to process
    files_to_process = entries
    if backup_type == "incremental" and previous_backup_dir:
        analysis = analyze_incremental(entries, previous_backup_dir, user=user)
        result.new_files = len(analysis.new_files)
        result.modified_files = len(analysis.modified_files)
        result.unchanged_files = len(analysis.unchanged_files)
        files_to_process = analysis.new_files + analysis.modified_files
    else:
        result.new_files = len(entries)
        result.modified_files = 0
        result.unchanged_files = 0

    manifest_entries: List[ManifestEntry] = []

    for i, entry in enumerate(files_to_process):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(user, i + 1, len(files_to_process), entry.path)

        sha = sha256_file(entry.path)
        if sha is None:
            result.errors += 1
            result.error_details.append({
                "user": user,
                "file": entry.path,
                "error": "Não foi possível calcular hash (sem permissão ou arquivo bloqueado)",
            })
            continue

        dest_filename = _safe_backup_name(entry.path, sha)
        dest_path = os.path.join(files_dir, dest_filename)
        backup_relative = os.path.join("files", dest_filename)

        try:
            shutil.copy2(entry.path, dest_path)
            result.copied += 1
            manifest_entries.append(ManifestEntry(
                source=entry.path,
                backup=backup_relative,
                size=entry.size,
                sha256=sha,
                mtime=datetime.fromtimestamp(entry.mtime).isoformat(),
            ))
        except PermissionError as e:
            result.errors += 1
            result.error_details.append({"user": user, "file": entry.path, "error": f"Sem permissão: {e}"})
        except OSError as e:
            result.errors += 1
            result.error_details.append({"user": user, "file": entry.path, "error": str(e)})

    manifest = make_manifest(
        manifest_entries,
        user=user,
        original_profile=original_profile,
        backup_type=backup_type,
        previous_backup_dir=previous_backup_dir or ""
    )
    result.manifest_path = save_manifest(manifest, user_backup_dir)
    return result


def run_multi_user_backup(
    entries_by_user: Dict[str, List[FileEntry]],
    profiles: List[UserProfile],
    destination: str,
    on_progress: Optional[Callable[[str, int, int, str, int, int], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    backup_type: str = "full",
    previous_backup_dir: Optional[str] = None,
    compression_level: CompressionLevel = CompressionLevel.NONE,
) -> MultiUserBackupResult:
    started = datetime.now()
    result = MultiUserBackupResult(compression_level=compression_level)
    ts = started.strftime("%Y-%m-%d_%H%M%S")
    backup_dir = os.path.join(destination, f"Backup_{ts}")
    users_dir = os.path.join(backup_dir, "usuarios")
    os.makedirs(users_dir, exist_ok=True)
    result.backup_dir = backup_dir

    total_files = sum(len(entries_by_user.get(profile.username, [])) for profile in profiles)
    copied_so_far = 0

    def handle_progress(user: str, i: int, total: int, path: str):
        if on_progress:
            on_progress(user, i, total, path, copied_so_far + i, total_files)

    for profile in profiles:
        if stop_flag and stop_flag():
            break
        user_dir = os.path.join(users_dir, profile.username)
        user_entries = entries_by_user.get(profile.username, [])
        user_result = run_user_backup(
            user_entries,
            profile.username,
            profile.path,
            user_dir,
            on_progress=handle_progress,
            stop_flag=stop_flag,
            backup_type=backup_type,
            previous_backup_dir=previous_backup_dir,
        )
        copied_so_far += user_result.copied
        result.user_results.append(user_result)
        result.error_details.extend(user_result.error_details)

    result.copied = sum(user_result.copied for user_result in result.user_results)
    result.skipped = sum(user_result.skipped for user_result in result.user_results)
    result.errors = sum(user_result.errors for user_result in result.user_results)
    result.elapsed_seconds = (datetime.now() - started).total_seconds()

    # Compress the multi-user backup if requested
    if compression_level != CompressionLevel.NONE:
        zip_path = os.path.join(destination, f"Backup_{ts}.zip")
        
        def compression_progress(current: int, total: int, path: str):
            pass  # Handle progress in UI if needed
        
        original_size, compressed_size = compress_directory(
            backup_dir,
            zip_path,
            compression_level,
            compression_progress
        )
        result.original_size = original_size
        result.compressed_size = compressed_size
        result.compressed_path = zip_path

    return result
