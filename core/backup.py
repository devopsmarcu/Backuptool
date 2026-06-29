import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Callable, Optional, Dict

from core.scanner import FileEntry
from core.manifest import (
    ManifestEntry, Manifest,
    build_manifest_entry, make_manifest, save_manifest,
    sha256_file, _safe_backup_name,
)
from core.profiles import UserProfile


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


def run_backup(
    entries: List[FileEntry],
    destination: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> BackupResult:
    result = BackupResult()
    total = len(entries)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir = os.path.join(destination, f"Backup_{ts}")
    files_dir = os.path.join(backup_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    result.backup_dir = backup_dir

    manifest_entries: List[ManifestEntry] = []

    for i, entry in enumerate(entries):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(i + 1, total, entry.path)

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
        manifest = make_manifest(manifest_entries)
        result.manifest_path = save_manifest(manifest, backup_dir)

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


def run_user_backup(
    entries: List[FileEntry],
    user: str,
    original_profile: str,
    user_backup_dir: str,
    on_progress: Optional[Callable[[str, int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> BackupResult:
    result = BackupResult(user=user, original_profile=original_profile)
    total = len(entries)
    files_dir = os.path.join(user_backup_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    result.backup_dir = user_backup_dir

    manifest_entries: List[ManifestEntry] = []

    for i, entry in enumerate(entries):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(user, i + 1, total, entry.path)

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

    manifest = make_manifest(manifest_entries, user=user, original_profile=original_profile)
    result.manifest_path = save_manifest(manifest, user_backup_dir)
    return result


def run_multi_user_backup(
    entries_by_user: Dict[str, List[FileEntry]],
    profiles: List[UserProfile],
    destination: str,
    on_progress: Optional[Callable[[str, int, int, str, int, int], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> MultiUserBackupResult:
    started = datetime.now()
    result = MultiUserBackupResult()
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
        )
        copied_so_far += user_result.copied
        result.user_results.append(user_result)
        result.error_details.extend(user_result.error_details)

    result.copied = sum(user_result.copied for user_result in result.user_results)
    result.skipped = sum(user_result.skipped for user_result in result.user_results)
    result.errors = sum(user_result.errors for user_result in result.user_results)
    result.elapsed_seconds = (datetime.now() - started).total_seconds()
    return result
