import os
import platform
import shutil
import csv
import json
import ntpath
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict

from core.manifest import Manifest, ManifestEntry, sha256_file, load_manifest, prepare_backup_path
from core.profiles import corporate_restore_destination, detect_user_profiles
from core.scanner import human_size
from core.compression import decompress_zip

try:
    from core.win_profile import create_or_get_profile_path, ProfileError
except ImportError:
    create_or_get_profile_path = None
    ProfileError = None


@dataclass
class RestoreResult:
    restored: int = 0
    skipped: int = 0
    overwritten: int = 0
    corrupted: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    details: List[dict] = field(default_factory=list)

    def add(self, status: str, source: str, dest: str, reason: str = ""):
        self.details.append({
            "status": status,
            "source": source,
            "dest": dest,
            "reason": reason,
        })


@dataclass
class CorporateRestorePlan:
    backup_dir: str
    manifest: Manifest
    manifest_path: str
    user_dir: str
    source_username: str
    destination_username: str
    destination: str
    domain: str = ""
    temp_dir: Optional[str] = None
    missing_files: int = 0
    corrupted_files: int = 0


@dataclass
class MultiUserRestoreResult:
    restored: int = 0
    skipped: int = 0
    overwritten: int = 0
    corrupted: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    user_results: List[dict] = field(default_factory=list)
    details: List[dict] = field(default_factory=list)


def run_restore(
    manifest: Manifest,
    backup_dir: str,
    mode: str = "all",
    selection: Optional[List[str]] = None,
    alternate_dest: str = "",
    conflict_mode: str = "overwrite",
    conflict_callback: Optional[Callable[[str], bool]] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> RestoreResult:
    result = RestoreResult()
    start = datetime.now()
    actual_backup_dir, temp_dir = prepare_backup_path(backup_dir)

    entries = _filter_entries(manifest.files, mode, selection)
    total = len(entries)

    for i, entry in enumerate(entries):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(i + 1, total, entry.source)

        stored_path = os.path.join(actual_backup_dir, entry.backup)
        if not os.path.isfile(stored_path):
            result.errors += 1
            result.add("error", entry.source, "", "Arquivo não encontrado no backup")
            continue

        actual_sha = sha256_file(stored_path)
        if actual_sha != entry.sha256:
            result.corrupted += 1
            result.add("corrupted", entry.source, stored_path,
                       f"SHA256 divergente: esperado {entry.sha256[:12]}… obtido {(actual_sha or 'erro')[:12]}…")
            continue

        dest_path = _resolve_dest(entry, mode, alternate_dest)

        if os.path.exists(dest_path):
            action = _handle_conflict(dest_path, conflict_mode, conflict_callback)
            if action == "skip":
                result.skipped += 1
                result.add("skipped", entry.source, dest_path, "Conflito: arquivo ignorado")
                continue
            elif action == "overwrite":
                result.overwritten += 1

        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(stored_path, dest_path)
            result.restored += 1
            result.add("restored", entry.source, dest_path)
        except PermissionError as e:
            result.errors += 1
            result.add("error", entry.source, dest_path, f"Sem permissão: {e}")
        except OSError as e:
            result.errors += 1
            result.add("error", entry.source, dest_path, str(e))

    result.elapsed_seconds = (datetime.now() - start).total_seconds()

    # Clean up temp dir
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def auto_map_users(source_users: List[str]) -> Dict[str, str]:
    dest_profiles = detect_user_profiles()
    dest_users = {profile.username.lower(): profile.username for profile in dest_profiles}
    mapping = {}
    for source_user in source_users:
        if source_user.lower() in dest_users:
            mapping[source_user] = dest_users[source_user.lower()]
    return mapping


def discover_corporate_restore_plans(backup_dir: str, user_mapping: Optional[Dict[str, str]] = None, domain: str = "") -> List[CorporateRestorePlan]:
    actual_backup_dir, temp_dir = prepare_backup_path(backup_dir)
    try:
        users_dir = os.path.join(actual_backup_dir, "usuarios")
        if not os.path.isdir(users_dir):
            return []
        
        # Get all source users
        source_users = []
        for username in sorted(os.listdir(users_dir), key=str.lower):
            user_dir = os.path.join(users_dir, username)
            manifest_path = os.path.join(user_dir, "manifest.json")
            if os.path.isfile(manifest_path):
                source_users.append(username)
        
        # Auto-map if no mapping provided
        if user_mapping is None:
            user_mapping = auto_map_users(source_users)
        
        plans: List[CorporateRestorePlan] = []
        for username in sorted(os.listdir(users_dir), key=str.lower):
            user_dir = os.path.join(users_dir, username)
            manifest_path = os.path.join(user_dir, "manifest.json")
            if not os.path.isfile(manifest_path):
                continue
            manifest = load_manifest(user_dir)
            source_user = manifest.user or username
            # Get destination user from mapping, default to source user
            dest_user = user_mapping.get(source_user, source_user)
            plans.append(CorporateRestorePlan(
                backup_dir=actual_backup_dir,
                manifest=manifest,
                manifest_path=manifest_path,
                user_dir=user_dir,
                source_username=source_user,
                destination_username=dest_user,
                destination=corporate_restore_destination(dest_user, domain),
                domain=domain,
                temp_dir=temp_dir,
            ))
        return plans
    finally:
        # Do not delete temp_dir here, let run_corporate_restore handle it
        pass


def validate_corporate_restore_plan(plan: CorporateRestorePlan) -> CorporateRestorePlan:
    missing = 0
    corrupted = 0
    for entry in plan.manifest.files:
        stored_path = os.path.join(plan.user_dir, entry.backup)
        if not os.path.isfile(stored_path):
            missing += 1
            continue
        actual_sha = sha256_file(stored_path)
        if actual_sha != entry.sha256:
            corrupted += 1
    plan.missing_files = missing
    plan.corrupted_files = corrupted
    return plan


def run_corporate_restore(
    plans: List[CorporateRestorePlan],
    conflict_mode: str = "overwrite",
    conflict_callback: Optional[Callable[[str], bool]] = None,
    on_progress: Optional[Callable[[str, int, int, str, int, int], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
    domain: str = "",
) -> MultiUserRestoreResult:
    started = datetime.now()
    result = MultiUserRestoreResult()
    total_files = sum(len(plan.manifest.files) for plan in plans)
    done_before_user = 0
    
    # Collect unique temp_dirs to clean up
    temp_dirs_to_clean = set()

    for plan in plans:
        if stop_flag and stop_flag():
            break
        
        if plan.temp_dir:
            temp_dirs_to_clean.add(plan.temp_dir)
            
        original_destination = plan.destination
        
        # Try to get or create Windows profile
        if platform.system() == "Windows" and create_or_get_profile_path and ProfileError:
            try:
                plan.destination = create_or_get_profile_path(plan.destination_username, domain)
            except ProfileError as e:
                result.details.append({
                    "status": "warning",
                    "source": f"user:{plan.destination_username}",
                    "dest": original_destination,
                    "reason": f"Perfil não registrado no Windows ({e}) — usando destino heurístico"
                })
        
        os.makedirs(plan.destination, exist_ok=True)
        user = plan.manifest.user or os.path.basename(plan.user_dir)

        def progress(i: int, total: int, path: str):
            if on_progress:
                on_progress(user, i, total, path, done_before_user + i, total_files)

        user_result = _run_corporate_user_restore(
            plan,
            conflict_mode=conflict_mode,
            conflict_callback=conflict_callback,
            on_progress=progress,
            stop_flag=stop_flag,
        )
        done_before_user += len(plan.manifest.files)
        result.user_results.append({
            "user": user,
            "destination": plan.destination,
            "total_files": len(plan.manifest.files),
            "result": user_result,
        })
        result.details.extend([
            {"user": user, **detail}
            for detail in user_result.details
        ])

    result.restored = sum(item["result"].restored for item in result.user_results)
    result.skipped = sum(item["result"].skipped for item in result.user_results)
    result.overwritten = sum(item["result"].overwritten for item in result.user_results)
    result.corrupted = sum(item["result"].corrupted for item in result.user_results)
    result.errors = sum(item["result"].errors for item in result.user_results)
    result.elapsed_seconds = (datetime.now() - started).total_seconds()
    
    # Clean up unique temp_dirs
    for temp_dir in temp_dirs_to_clean:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    return result


def _run_corporate_user_restore(
    plan: CorporateRestorePlan,
    conflict_mode: str,
    conflict_callback: Optional[Callable[[str], bool]],
    on_progress: Optional[Callable[[int, int, str], None]],
    stop_flag: Optional[Callable[[], bool]],
) -> RestoreResult:
    result = RestoreResult()
    start = datetime.now()
    total = len(plan.manifest.files)

    for i, entry in enumerate(plan.manifest.files):
        if stop_flag and stop_flag():
            break
        if on_progress:
            on_progress(i + 1, total, entry.source)

        stored_path = os.path.join(plan.user_dir, entry.backup)
        if not os.path.isfile(stored_path):
            result.errors += 1
            result.add("error", entry.source, "", "Arquivo não encontrado no backup")
            continue

        actual_sha = sha256_file(stored_path)
        if actual_sha != entry.sha256:
            result.corrupted += 1
            result.add("corrupted", entry.source, stored_path,
                       f"SHA256 divergente: esperado {entry.sha256[:12]}… obtido {(actual_sha or 'erro')[:12]}…")
            continue

        relative_path = _profile_relative_path(entry, plan.manifest, plan.source_username, plan.destination_username)
        dest_path = os.path.join(plan.destination, relative_path)

        if os.path.exists(dest_path):
            action = _handle_conflict(dest_path, conflict_mode, conflict_callback)
            if action == "skip":
                result.skipped += 1
                result.add("skipped", entry.source, dest_path, "Conflito: arquivo ignorado")
                continue
            if action == "overwrite":
                result.overwritten += 1

        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(stored_path, dest_path)
            result.restored += 1
            result.add("restored", entry.source, dest_path)
        except PermissionError as e:
            result.errors += 1
            result.add("error", entry.source, dest_path, f"Sem permissão: {e}")
        except OSError as e:
            result.errors += 1
            result.add("error", entry.source, dest_path, str(e))

    result.elapsed_seconds = (datetime.now() - start).total_seconds()
    return result


def _profile_relative_path(entry: ManifestEntry, manifest: Manifest, source_username: Optional[str] = None, dest_username: Optional[str] = None) -> str:
    path = Path(entry.source)
    
    # If user mapping is provided, replace source username with dest username in path
    if source_username and dest_username:
        parts = list(path.parts)
        if manifest.os == "Windows":
            # Windows: C:\Users\source_username\... -> C:\Users\dest_username\...
            if len(parts) >= 3 and parts[1].lower() == "users" and parts[2] == source_username:
                parts[2] = dest_username
                path = Path(*parts)
        else:
            # Linux/macOS: /home/source_username/... -> /home/dest_username/...
            if len(parts) >= 3 and parts[1] == "home" and parts[2] == source_username:
                parts[2] = dest_username
                path = Path(*parts)
    
    if manifest.original_profile:
        # Check if we need to adjust original profile for user mapping
        original_profile_parts = Path(manifest.original_profile).parts
        adjusted_original_profile = manifest.original_profile
        if source_username and dest_username:
            if manifest.os == "Windows":
                if len(original_profile_parts) >= 3 and original_profile_parts[1].lower() == "users" and original_profile_parts[2] == source_username:
                    adjusted_parts = list(original_profile_parts)
                    adjusted_parts[2] = dest_username
                    adjusted_original_profile = str(Path(*adjusted_parts))
            else:
                if len(original_profile_parts) >= 3 and original_profile_parts[1] == "home" and original_profile_parts[2] == source_username:
                    adjusted_parts = list(original_profile_parts)
                    adjusted_parts[2] = dest_username
                    adjusted_original_profile = str(Path(*adjusted_parts))
        
        try:
            if "\\" in adjusted_original_profile or ":" in adjusted_original_profile:
                return ntpath.relpath(str(path), adjusted_original_profile)
            else:
                return os.path.relpath(str(path), adjusted_original_profile)
        except ValueError:
            pass
    return os.path.basename(str(path))


def _filter_entries(
    entries: List[ManifestEntry],
    mode: str,
    selection: Optional[List[str]],
) -> List[ManifestEntry]:
    if mode == "selection" and selection:
        sel_set = set(selection)
        return [e for e in entries if e.source in sel_set]
    return entries


def _resolve_dest(entry: ManifestEntry, mode: str, alternate_dest: str) -> str:
    if mode == "alternate" and alternate_dest:
        return os.path.join(alternate_dest, Path(entry.source).name)
    return entry.source


def _handle_conflict(
    dest_path: str,
    conflict_mode: str,
    conflict_callback: Optional[Callable[[str], bool]],
) -> str:
    if conflict_mode == "overwrite":
        return "overwrite"
    if conflict_mode == "ignore":
        return "skip"
    if conflict_mode == "ask" and conflict_callback:
        return "overwrite" if conflict_callback(dest_path) else "skip"
    return "skip"


def generate_restore_report(
    result: RestoreResult,
    manifest: Manifest,
    output_dir: str = "logs",
) -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = os.path.join(output_dir, f"restore_{ts}.json")
    report = {
        "timestamp": datetime.now().isoformat(),
        "source_machine": manifest.machine,
        "backup_date": manifest.backup_date,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "summary": {
            "restored": result.restored,
            "skipped": result.skipped,
            "overwritten": result.overwritten,
            "corrupted": result.corrupted,
            "errors": result.errors,
        },
        "details": result.details,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(output_dir, f"restore_{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["status", "source", "dest", "reason"])
        writer.writeheader()
        writer.writerows(result.details)

    return json_path, csv_path


def get_manifest_roots(manifest: Manifest) -> List[str]:
    roots = set()
    for entry in manifest.files:
        parts = Path(entry.source).parts
        if len(parts) >= 2:
            roots.add(str(Path(*parts[:4])) if len(parts) >= 4 else entry.source)
    return sorted(roots)
