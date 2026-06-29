import os
import json
import csv
from datetime import datetime
from typing import List

from core.scanner import FileEntry, human_size
from core.backup import BackupResult, MultiUserBackupResult
from core.restore import MultiUserRestoreResult


def generate_report(
    entries: List[FileEntry],
    result: BackupResult,
    destination: str,
    technician: str = "",
    machine: str = "",
    output_dir: str = "logs",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"backup_{timestamp}.json")
    csv_path = os.path.join(output_dir, f"backup_{timestamp}.csv")

    total_bytes = sum(e.size for e in entries)

    report = {
        "timestamp": datetime.now().isoformat(),
        "technician": technician,
        "machine": machine,
        "destination": destination,
        "backup_dir": result.backup_dir,
        "manifest": result.manifest_path,
        "summary": {
            "total_files_scanned": len(entries),
            "files_copied": result.copied,
            "files_skipped": result.skipped,
            "files_with_error": result.errors,
            "total_size": human_size(total_bytes),
            "total_size_bytes": total_bytes,
        },
        "errors": result.error_details,
        "files": [
            {
                "path": e.path,
                "relative": e.relative_path,
                "size": e.size,
                "size_human": human_size(e.size),
            }
            for e in entries
        ],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "relative", "size_bytes", "size_human"])
        for e in entries:
            writer.writerow([e.path, e.relative_path, e.size, human_size(e.size)])

    return json_path


def generate_multi_user_backup_report(
    result: MultiUserBackupResult,
    destination: str,
    technician: str = "",
    machine: str = "",
) -> tuple[str, str]:
    json_path = os.path.join(result.backup_dir, "relatorio.json")
    csv_path = os.path.join(result.backup_dir, "relatorio.csv")

    users = []
    for user_result in result.user_results:
        total_files = user_result.copied + user_result.errors + user_result.skipped
        users.append({
            "user": user_result.user,
            "original_profile": user_result.original_profile,
            "manifest": user_result.manifest_path,
            "files_copied": user_result.copied,
            "files_skipped": user_result.skipped,
            "files_with_error": user_result.errors,
            "total_files": total_files,
            "errors": user_result.error_details,
        })

    report = {
        "timestamp": datetime.now().isoformat(),
        "technician": technician,
        "machine": machine,
        "destination": destination,
        "backup_dir": result.backup_dir,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "summary": {
            "users": len(result.user_results),
            "files_copied": result.copied,
            "files_skipped": result.skipped,
            "files_with_error": result.errors,
        },
        "users": users,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "user", "original_profile", "manifest", "total_files",
            "files_copied", "files_skipped", "files_with_error", "elapsed_seconds",
        ])
        for user in users:
            writer.writerow([
                user["user"],
                user["original_profile"],
                user["manifest"],
                user["total_files"],
                user["files_copied"],
                user["files_skipped"],
                user["files_with_error"],
                round(result.elapsed_seconds, 2),
            ])

    return json_path, csv_path


def generate_multi_user_restore_report(
    result: MultiUserRestoreResult,
    output_dir: str = "logs",
) -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"restore_corporativo_{ts}.json")
    csv_path = os.path.join(output_dir, f"restore_corporativo_{ts}.csv")

    report = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "summary": {
            "users": len(result.user_results),
            "restored": result.restored,
            "skipped": result.skipped,
            "overwritten": result.overwritten,
            "corrupted": result.corrupted,
            "errors": result.errors,
        },
        "users": [
            {
                "user": item["user"],
                "destination": item["destination"],
                "total_files": item["total_files"],
                "restored": item["result"].restored,
                "skipped": item["result"].skipped,
                "overwritten": item["result"].overwritten,
                "corrupted": item["result"].corrupted,
                "errors": item["result"].errors,
                "elapsed_seconds": round(item["result"].elapsed_seconds, 2),
            }
            for item in result.user_results
        ],
        "details": result.details,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "user", "destination", "total_files", "restored", "skipped",
            "overwritten", "corrupted", "errors", "elapsed_seconds",
        ])
        for item in report["users"]:
            writer.writerow([
                item["user"],
                item["destination"],
                item["total_files"],
                item["restored"],
                item["skipped"],
                item["overwritten"],
                item["corrupted"],
                item["errors"],
                item["elapsed_seconds"],
            ])

    return json_path, csv_path
