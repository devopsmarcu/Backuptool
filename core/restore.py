import os
import shutil
import csv
import json
import ntpath
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable

from core.manifest import Manifest, ManifestEntry, sha256_file, load_manifest
from core.profiles import corporate_restore_destination
from core.scanner import human_size


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
    destination: str
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
    entries = _filter_entries(manifest.files, mode, selection)
    total = len(entries)

    for i, entry in enumerate(entries):
        if stop_flag and stop_flag():
            break

        if on_progress:
            on_progress(i + 1, total, entry.source)

        stored_path = os.path.join(backup_dir, entry.backup)
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
    return result


def discover_corporate_restore_plans(backup_dir: str) -> List[CorporateRestorePlan]:
    users_dir = os.path.join(backup_dir, "usuarios")
    if not os.path.isdir(users_dir):
        return []

    plans: List[CorporateRestorePlan] = []
    for username in sorted(os.listdir(users_dir), key=str.lower):
        user_dir = os.path.join(users_dir, username)
        manifest_path = os.path.join(user_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        manifest = load_manifest(user_dir)
        user = manifest.user or username
        plans.append(CorporateRestorePlan(
            backup_dir=backup_dir,
            manifest=manifest,
            manifest_path=manifest_path,
            user_dir=user_dir,
            destination=corporate_restore_destination(user),
        ))
    return plans


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
) -> MultiUserRestoreResult:
    started = datetime.now()
    result = MultiUserRestoreResult()
    total_files = sum(len(plan.manifest.files) for plan in plans)
    done_before_user = 0

    for plan in plans:
        if stop_flag and stop_flag():
            break
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

        relative_path = _profile_relative_path(entry, plan.manifest)
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


def _profile_relative_path(entry: ManifestEntry, manifest: Manifest) -> str:
    if manifest.original_profile:
        if "\\" in manifest.original_profile or ":" in manifest.original_profile:
            return ntpath.relpath(entry.source, manifest.original_profile)
        try:
            return os.path.relpath(entry.source, manifest.original_profile)
        except ValueError:
            pass
    return os.path.basename(entry.source)


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
