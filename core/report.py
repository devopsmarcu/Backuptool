import os
import json
import csv
from datetime import datetime
from typing import List

from core.scanner import FileEntry, human_size
from core.backup import BackupResult, MultiUserBackupResult
from core.restore import MultiUserRestoreResult


def generate_html_report(report_data: dict) -> str:
    """Generate an HTML report from report data."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backup Report - {report_data.get('timestamp', '')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f0f8ff; padding: 20px; border-radius: 8px; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #2563eb; }}
        .summary-card p {{ margin: 0; font-size: 24px; font-weight: bold; }}
        .errors {{ background: #ffebee; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .errors h3 {{ color: #dc2626; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Backup Report</h1>
        <p><strong>Timestamp:</strong> {report_data.get('timestamp', '')}</p>
        <p><strong>Machine:</strong> {report_data.get('machine', '')}</p>
        <p><strong>Technician:</strong> {report_data.get('technician', '')}</p>
        <p><strong>Backup Directory:</strong> {report_data.get('backup_dir', '')}</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Files Scanned</h3>
                <p>{report_data.get('summary', {}).get('total_files_scanned', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files Copied</h3>
                <p>{report_data.get('summary', {}).get('files_copied', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files Skipped</h3>
                <p>{report_data.get('summary', {}).get('files_skipped', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files with Errors</h3>
                <p>{report_data.get('summary', {}).get('files_with_error', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Total Size</h3>
                <p>{report_data.get('summary', {}).get('total_size', '')}</p>
            </div>
        </div>
"""

    if report_data.get('errors'):
        html += f"""
        <div class="errors">
            <h3>Errors ({len(report_data['errors'])})</h3>
            <ul>
                {''.join([f'<li>{err["file"]}: {err["error"]}</li>' for err in report_data['errors']])}
            </ul>
        </div>
"""

    html += """
    </div>
</body>
</html>
"""
    return html


def generate_report(
    entries: List[FileEntry],
    result: BackupResult,
    destination: str,
    technician: str = "",
    machine: str = "",
    output_dir: str = "logs",
    export_to_backup_dir: bool = True,
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
            "backup_type": result.backup_type,
            "new_files": result.new_files,
            "modified_files": result.modified_files,
            "unchanged_files": result.unchanged_files,
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

    # Also export to backup directory
    if export_to_backup_dir and result.backup_dir:
        backup_json_path = os.path.join(result.backup_dir, "backup_report.json")
        backup_csv_path = os.path.join(result.backup_dir, "backup_report.csv")
        backup_html_path = os.path.join(result.backup_dir, "backup_report.html")

        with open(backup_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        with open(backup_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["path", "relative", "size_bytes", "size_human"])
            for e in entries:
                writer.writerow([e.path, e.relative_path, e.size, human_size(e.size)])

        with open(backup_html_path, "w", encoding="utf-8") as f:
            f.write(generate_html_report(report))

    return json_path


def generate_multi_user_backup_report(
    result: MultiUserBackupResult,
    destination: str,
    technician: str = "",
    machine: str = "",
) -> tuple[str, str]:
    json_path = os.path.join(result.backup_dir, "relatorio.json")
    csv_path = os.path.join(result.backup_dir, "relatorio.csv")
    html_path = os.path.join(result.backup_dir, "relatorio.html")

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

    # Generate HTML report
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Multi-User Backup Report - {report.get('timestamp', '')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f0f8ff; padding: 20px; border-radius: 8px; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #2563eb; }}
        .summary-card p {{ margin: 0; font-size: 24px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Multi-User Backup Report</h1>
        <p><strong>Timestamp:</strong> {report.get('timestamp', '')}</p>
        <p><strong>Machine:</strong> {report.get('machine', '')}</p>
        <p><strong>Technician:</strong> {report.get('technician', '')}</p>
        <p><strong>Backup Directory:</strong> {report.get('backup_dir', '')}</p>
        <p><strong>Elapsed Time:</strong> {report.get('elapsed_seconds', 0)} seconds</p>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Users</h3>
                <p>{report.get('summary', {}).get('users', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files Copied</h3>
                <p>{report.get('summary', {}).get('files_copied', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files Skipped</h3>
                <p>{report.get('summary', {}).get('files_skipped', 0)}</p>
            </div>
            <div class="summary-card">
                <h3>Files with Errors</h3>
                <p>{report.get('summary', {}).get('files_with_error', 0)}</p>
            </div>
        </div>
        
        <h2>User Details</h2>
        <table>
            <tr>
                <th>User</th>
                <th>Original Profile</th>
                <th>Files Copied</th>
                <th>Files Skipped</th>
                <th>Files with Errors</th>
                <th>Total Files</th>
            </tr>
            {''.join([f'''
            <tr>
                <td>{user["user"]}</td>
                <td>{user["original_profile"]}</td>
                <td>{user["files_copied"]}</td>
                <td>{user["files_skipped"]}</td>
                <td>{user["files_with_error"]}</td>
                <td>{user["total_files"]}</td>
            </tr>
            ''' for user in users])}
        </table>
    </div>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

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
