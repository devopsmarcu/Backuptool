"""
ui/workers.py — Workers assíncronos (QThread) que chamam as funções de
negócio existentes em core/ e config/ SEM alterá-las.

Na versão CustomTkinter, o padrão era `threading.Thread` + `self.after(0, ...)`
para voltar à thread da UI. Em Qt o equivalente correto é QThread + Signals
(uma conexão Signal→Slot entre threads diferentes é automaticamente
enfileirada pelo Qt e entregue na thread da GUI). A lógica chamada dentro
de cada worker é exatamente a mesma dos módulos core/*, só a "cola" com a
interface gráfica muda.
"""

from __future__ import annotations

import os
import socket
import threading
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.scanner import scan_paths, scan_profile_path, total_size
from core.backup import run_backup, run_multi_user_backup
from core.report import generate_report, generate_multi_user_backup_report, generate_multi_user_restore_report
from core.restore import run_restore, generate_restore_report, run_corporate_restore


class ScanWorker(QThread):
    """Replica `_scan_thread` da versão CustomTkinter (aba Resumo)."""

    files_found = Signal(int)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, paths, exclusions, excl_exts, selected_profiles, destination, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.exclusions = exclusions
        self.excl_exts = excl_exts
        self.selected_profiles = selected_profiles
        self.destination = destination

    def run(self):
        try:
            count = [0]

            def on_file(_path):
                count[0] += 1
                if count[0] % 50 == 0:
                    self.files_found.emit(count[0])

            res_data: dict = {}
            scanned_by_user: dict = {}

            if self.selected_profiles:
                scanned = []
                total_b = 0
                user_lines = []
                for profile in self.selected_profiles:
                    entries = scan_profile_path(profile.path, self.exclusions, self.excl_exts, on_file)
                    scanned_by_user[profile.username] = entries
                    scanned.extend(entries)
                    user_total = total_size(entries)
                    total_b += user_total
                    user_lines.append(f"{profile.username}: {len(entries)} arquivos · {_human(user_total)}")
                res_data["users_text"] = "\n".join(user_lines)
                res_data["stats_text"] = f"Arquivos: {len(scanned)}\nTamanho: {_human(total_b)}"
            else:
                scanned = scan_paths(self.paths, self.exclusions, self.excl_exts, on_file)
                total_b = total_size(scanned)
                res_data["users_text"] = "Pastas incluídas:\n" + "\n".join(f"- {p}" for p in self.paths)
                res_data["stats_text"] = f"Arquivos: {len(scanned)}\nTamanho: {_human(total_b)}"

            res_data["dest_text"] = f"Destino: {self.destination}"
            try:
                import shutil
                free = shutil.disk_usage(self.destination).free
                res_data["dest_text"] += f"\nEspaço livre: {_human(free)}"
            except OSError:
                res_data["dest_text"] += "\nEspaço livre: não disponível"

            excl_list = [f"- {item}" for item in self.exclusions[:12]]
            if len(self.exclusions) > 12:
                excl_list.append(f"- ... e mais {len(self.exclusions) - 12} exclusões")
            res_data["excl_text"] = "\n".join(excl_list)

            res_data["scanned"] = scanned
            res_data["scanned_by_user"] = scanned_by_user
            self.finished_ok.emit(res_data)
        except Exception as exc:  # pragma: no cover - defensivo, igual ao espírito do original
            self.failed.emit(str(exc))


def _human(n):
    from core.scanner import human_size
    return human_size(n)


class BackupWorker(QThread):
    """Replica `_backup_thread` (backup único ou multiusuário)."""

    progress_single = Signal(int, int, str)
    progress_multi = Signal(str, int, int, str, int, int)
    finished_single = Signal(object, str)
    finished_multi = Signal(object, str, str)
    failed = Signal(str)

    def __init__(self, state, logs_dir: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.logs_dir = logs_dir
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            if self.state.selected_profiles and self.state.scanned_by_user:
                def on_user_progress(user, i, t, path, copied, total):
                    self.progress_multi.emit(user, i, t, path, copied, total)

                result = run_multi_user_backup(
                    self.state.scanned_by_user,
                    self.state.selected_profiles,
                    self.state.destination,
                    on_progress=on_user_progress,
                    stop_flag=lambda: self._stop_flag,
                )
                report_path, csv_path = generate_multi_user_backup_report(
                    result,
                    self.state.destination,
                    technician=self.state.technician,
                    machine=socket.gethostname(),
                )
                self.finished_multi.emit(result, report_path, csv_path)
                return

            def on_progress(i, t, path):
                self.progress_single.emit(i, t, path)

            result = run_backup(
                self.state.scanned,
                self.state.destination,
                on_progress=on_progress,
                stop_flag=lambda: self._stop_flag,
            )
            report_path = generate_report(
                self.state.scanned, result, self.state.destination,
                technician=self.state.technician,
                machine=socket.gethostname(),
                output_dir=self.logs_dir,
            )
            self.finished_single.emit(result, report_path)
        except Exception as exc:
            self.failed.emit(str(exc))


class RestoreWorker(QThread):
    """Replica `_restore_thread` (restauração a partir de manifest.json único)."""

    progress = Signal(int, int, str)
    finished_ok = Signal(object, str, str)
    failed = Signal(str)
    confirm_conflict = Signal(str, object)  # (caminho, container de resposta {"value": bool, "event": Event})

    def __init__(self, manifest, backup_dir, mode, selection, alternate, conflict_mode, logs_dir, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.backup_dir = backup_dir
        self.mode = mode
        self.selection = selection
        self.alternate = alternate
        self.conflict_mode = conflict_mode
        self.logs_dir = logs_dir
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def _conflict_callback(self, dest_path: str) -> bool:
        container = {"value": False, "event": threading.Event()}
        self.confirm_conflict.emit(dest_path, container)
        container["event"].wait()
        return container["value"]

    def run(self):
        try:
            def on_progress(i, t, path):
                self.progress.emit(i, t, path)

            result = run_restore(
                manifest=self.manifest,
                backup_dir=self.backup_dir,
                mode=self.mode,
                selection=self.selection if self.mode == "selection" else None,
                alternate_dest=self.alternate,
                conflict_mode=self.conflict_mode,
                conflict_callback=self._conflict_callback if self.conflict_mode == "ask" else None,
                on_progress=on_progress,
                stop_flag=lambda: self._stop_flag,
            )
            json_path, csv_path = generate_restore_report(
                result, self.manifest, output_dir=self.logs_dir,
            )
            self.finished_ok.emit(result, json_path, csv_path)
        except Exception as exc:
            self.failed.emit(str(exc))


class CorporateRestoreWorker(QThread):
    """Replica `_corporate_restore_thread` (restauração multiusuário corporativa)."""

    progress = Signal(str, int, int, str, int, int)
    finished_ok = Signal(object, str, str)
    failed = Signal(str)
    confirm_conflict = Signal(str, object)

    def __init__(self, plans, conflict_mode, logs_dir, parent=None):
        super().__init__(parent)
        self.plans = plans
        self.conflict_mode = conflict_mode
        self.logs_dir = logs_dir
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def _conflict_callback(self, dest_path: str) -> bool:
        container = {"value": False, "event": threading.Event()}
        self.confirm_conflict.emit(dest_path, container)
        container["event"].wait()
        return container["value"]

    def run(self):
        try:
            def on_progress(user, i, t, path, done, total):
                self.progress.emit(user, i, t, path, done, total)

            result = run_corporate_restore(
                self.plans,
                conflict_mode=self.conflict_mode,
                conflict_callback=self._conflict_callback if self.conflict_mode == "ask" else None,
                on_progress=on_progress,
                stop_flag=lambda: self._stop_flag,
            )
            json_path, csv_path = generate_multi_user_restore_report(result, output_dir=self.logs_dir)
            self.finished_ok.emit(result, json_path, csv_path)
        except Exception as exc:
            self.failed.emit(str(exc))
