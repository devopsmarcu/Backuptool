"""
ui/pages/backup_page.py — Aba "5 · Backup".

Porta de `_build_tab_progresso` / `_start_backup` / `_backup_thread` /
`_update_progress` / `_update_user_progress` / `_backup_done` /
`_multi_backup_done`. A execução roda em `ui.workers.BackupWorker`
(QThread) — as funções de negócio chamadas (`run_backup`,
`run_multi_user_backup`, `generate_report`, ...) são as mesmas de
`core.backup` / `core.report`, inalteradas.

O log detalhado não fica mais embutido nesta página: é enviado via sinal
`log_message` para a página "Logs" (menu principal), mantendo esta tela
focada no acompanhamento em tempo real (métricas + progresso).
"""

from __future__ import annotations

import os
import shutil
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QProgressBar, QMessageBox

from core.destinations import validate_destination
from core.scanner import human_size, total_size
from ui.format_utils import format_duration, estimate_remaining, short_path, friendly_error
from ui.os_utils import open_path
from ui.state import AppState
from ui.widgets import Card, SectionIntro, SuccessButton, DangerButton, SecondaryButton, MetricTile
from ui.workers import BackupWorker


class BackupPage(QWidget):
    log_message = Signal(str)
    backup_finished = Signal(bool)  # True se concluído sem erros
    open_logs_requested = Signal()

    def __init__(self, state: AppState, logs_dir: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        self._worker: BackupWorker | None = None
        self._started_at = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Execução do backup",
            "Acompanhe usuário atual, arquivo processado, progresso e tempo estimado restante.",
        ))

        status_card = Card("Monitoramento de Cópia")
        tiles = QGridLayout()
        tiles.setSpacing(10)
        self.tile_user = MetricTile("Usuário atual", "Aguardando início")
        self.tile_file = MetricTile("Arquivo atual", "Aguardando início")
        self.tile_time = MetricTile("Tempo", "0s · restante calculando...")
        tiles.addWidget(self.tile_user, 0, 0)
        tiles.addWidget(self.tile_file, 0, 1)
        tiles.addWidget(self.tile_time, 0, 2)
        status_card.body_layout().addLayout(tiles)
        root.addWidget(status_card)

        progress_row = QHBoxLayout()
        self.progressbar = QProgressBar()
        self.progressbar.setValue(0)
        self.lbl_percentage = QLabel("0%")
        self.lbl_percentage.setFixedWidth(48)
        self.lbl_percentage.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.progressbar, 1)
        progress_row.addWidget(self.lbl_percentage)
        root.addLayout(progress_row)

        self.lbl_counter = QLabel("Progresso: 0 / 0 arquivos")
        self.lbl_counter.setObjectName("Muted")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self.lbl_counter)

        log_card = Card("Últimas atividades")
        self.lbl_last_activity = QLabel("Nenhuma atividade ainda.")
        self.lbl_last_activity.setObjectName("Muted")
        self.lbl_last_activity.setWordWrap(True)
        log_card.body_layout().addWidget(self.lbl_last_activity)
        btn_view_logs = SecondaryButton("Ver logs completos →")
        btn_view_logs.clicked.connect(self.open_logs_requested)
        log_card.body_layout().addWidget(btn_view_logs, 0, Qt.AlignmentFlag.AlignLeft)
        self.btn_view_logs = btn_view_logs
        root.addWidget(log_card)

        btn_row = QHBoxLayout()
        self.btn_start = SuccessButton("Iniciar Backup")
        self.btn_start.clicked.connect(self._start_backup)
        self.btn_stop = DangerButton("Cancelar Backup")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_backup)
        btn_report = SecondaryButton("Abrir Relatório")
        btn_report.clicked.connect(lambda: open_path(self, self.state.last_report_path))
        btn_folder = SecondaryButton("Abrir Pasta")
        btn_folder.clicked.connect(lambda: open_path(self, self.state.last_backup_dir))
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(btn_report)
        btn_row.addWidget(btn_folder)
        btn_row.addStretch(1)
        self.lbl_final_status = QLabel("")
        btn_row.addWidget(self.lbl_final_status)
        root.addLayout(btn_row)
        root.addStretch(1)

    # ── início / parada ──
    def _start_backup(self):
        if not self.state.scanned:
            QMessageBox.warning(self, "Scan necessário",
                                 "Execute o scan na aba Resumo antes de iniciar o backup.")
            return
        if not self._validate_ready():
            return

        self._started_at = time.time()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_final_status.setText("")
        self.tile_user.set_value("Preparando...")
        self.tile_file.set_value("Preparando...")
        self.tile_time.set_value("0s · restante calculando...")
        self.lbl_last_activity.setText("Iniciando cópia...")

        self._worker = BackupWorker(self.state, self.logs_dir)
        self._worker.progress_single.connect(self._on_progress_single)
        self._worker.progress_multi.connect(self._on_progress_multi)
        self._worker.finished_single.connect(self._on_finished_single)
        self._worker.finished_multi.connect(self._on_finished_multi)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _stop_backup(self):
        if self._worker:
            self._worker.request_stop()
        self.btn_stop.setEnabled(False)

    def _validate_ready(self) -> bool:
        valid, msg = validate_destination(self.state.destination)
        if not valid:
            QMessageBox.critical(self, "Destino não está pronto", friendly_error(msg))
            return False
        try:
            free = shutil.disk_usage(self.state.destination).free
            required = total_size(self.state.scanned)
            if required > free:
                QMessageBox.critical(
                    self, "Espaço insuficiente",
                    f"O destino possui {human_size(free)} livres, mas o backup precisa de "
                    f"aproximadamente {human_size(required)}.",
                )
                return False
        except OSError:
            QMessageBox.warning(
                self, "Não foi possível conferir o espaço",
                "O destino será usado, mas não foi possível confirmar o espaço livre antes de iniciar.",
            )
        return True

    # ── progresso ──
    def _set_progress(self, done: int, total: int):
        pct = done / total if total else 0
        self.progressbar.setValue(int(pct * 100))
        self.lbl_percentage.setText(f"{int(pct * 100)}%")
        self.lbl_counter.setText(f"Progresso: {done} / {total} arquivos")
        elapsed = format_duration(time.time() - self._started_at)
        remaining = estimate_remaining(self._started_at, done, total)
        self.tile_time.set_value(f"{elapsed} · restante {remaining}")

    def _on_progress_single(self, i: int, total: int, path: str):
        self._set_progress(i, total)
        self.tile_user.set_value("Backup manual")
        self.tile_file.set_value(short_path(path))
        line = f"[{i:>5}/{total}] {os.path.basename(path)}"
        self.lbl_last_activity.setText(line)
        self.log_message.emit(line + "\n")

    def _on_progress_multi(self, user, i, total, path, copied, overall_total):
        self._set_progress(copied, overall_total)
        self.tile_user.set_value(user)
        self.tile_file.set_value(short_path(path))
        line = f"[{copied:>5}/{overall_total}] {user}: {os.path.basename(path)}"
        self.lbl_last_activity.setText(line)
        self.log_message.emit(line + "\n")

    # ── finalização ──
    def _finish_common(self, result, report_path: str, extra_lines: list[str]):
        self.progressbar.setValue(100)
        self.lbl_percentage.setText("100%")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.state.last_backup_dir = result.backup_dir
        self.state.last_report_path = report_path

        if result.errors == 0:
            msg = f"✔ Concluído — {result.copied} arquivos copiados"
            self.lbl_final_status.setStyleSheet("color: #22C55E; font-weight: 700;")
        else:
            msg = f"⚠ Concluído com erros — {result.copied} copiados, {result.errors} erros"
            self.lbl_final_status.setStyleSheet("color: #F59E0B; font-weight: 700;")

        self.lbl_final_status.setText(msg)
        self.lbl_last_activity.setText(msg)
        self.log_message.emit(f"\n{msg}\n")
        for line in extra_lines:
            self.log_message.emit(line + "\n")

        if result.errors:
            self.log_message.emit("\n── Erros ──\n")
            for err in result.error_details:
                user_prefix = f"{err.get('user', '')} " if err.get("user") else ""
                self.log_message.emit(f"  {user_prefix}{err['file']}: {err['error']}\n")

        self.backup_finished.emit(result.errors == 0)

    def _on_finished_single(self, result, report_path: str):
        extra = []
        if getattr(result, "manifest_path", None):
            extra.append(f"manifest.json: {result.manifest_path}")
        extra.append(f"Relatório:     {report_path}")
        self._finish_common(result, report_path, extra)

    def _on_finished_multi(self, result, report_path: str, csv_path: str):
        extra = [
            f"Backup:        {result.backup_dir}",
            f"Relatório JSON: {report_path}",
            f"Relatório CSV : {csv_path}",
        ]
        for user_result in result.user_results:
            extra.append(f"  {user_result.user}: {user_result.copied} copiados, {user_result.errors} erros")
        self._finish_common(result, report_path, extra)

    def _on_failed(self, message: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        QMessageBox.critical(self, "Erro durante o backup", friendly_error(message))
