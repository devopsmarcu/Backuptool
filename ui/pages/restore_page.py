"""
ui/pages/restore_page.py — Aba "6 · Restaurar".

Porta fiel de `_build_tab_restaurar` e de todos os seus handlers
(`_load_manifest`, `_populate_corporate_preview`, `_populate_selection`,
`_on_restore_mode_change`, `_start_restore`, `_restore_thread`,
`_corporate_restore_thread`, `_restore_done`, `_corporate_restore_done`).

Toda a lógica de negócio (`core.restore.*`) permanece exatamente igual;
apenas a "cola" com a interface muda para QThread + Signals (ver
`ui.workers.RestoreWorker` / `CorporateRestoreWorker`).
"""

from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QFileDialog,
    QRadioButton, QButtonGroup, QProgressBar, QMessageBox, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QSizePolicy,
)

import platform

from core.manifest import load_manifest, Manifest
from core.restore import get_manifest_roots, discover_corporate_restore_plans, validate_corporate_restore_plan
from styles import dark_theme as theme
from styles.svg_icons import icon_html
from ui.format_utils import format_duration, estimate_remaining, short_path, friendly_error
from ui.os_utils import open_path
from ui.state import AppState
from ui.widgets import Card, SectionIntro, RestoreActionButton, DangerButton, SecondaryButton, MetricTile
from ui.workers import RestoreWorker, CorporateRestoreWorker

try:
    from core.win_profile import is_admin
except ImportError:
    is_admin = None


class RestorePage(QWidget):
    log_message = Signal(str)
    restore_finished = Signal(bool)
    open_logs_requested = Signal()

    def __init__(self, state: AppState, logs_dir: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)
        self._worker: RestoreWorker | CorporateRestoreWorker | None = None
        self._started_at = 0.0
        self._selection_items: dict[str, QListWidgetItem] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Restauração",
            "Selecione uma pasta de backup, valide os arquivos e acompanhe a restauração com segurança.",
        ))

        # ── Origem ──
        src_card = Card("Origem do Backup")
        src_row = QHBoxLayout()
        self.src_entry = QLineEdit()
        self.src_entry.setPlaceholderText("Pasta do backup")
        btn_browse_src = RestoreActionButton("Procurar")
        btn_browse_src.clicked.connect(self._browse_restore_src)
        src_row.addWidget(self.src_entry, 1)
        src_row.addWidget(btn_browse_src)
        src_card.body_layout().addLayout(src_row)
        self.lbl_manifest_info = QLabel("")
        self.lbl_manifest_info.setWordWrap(True)
        src_card.body_layout().addWidget(self.lbl_manifest_info)
        root.addWidget(src_card)

        # ── Validação / mapeamento ──
        val_card = Card("Validação e Mapeamento")
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preview_scroll.setMinimumHeight(120)
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.addStretch(1)
        self.preview_scroll.setWidget(self.preview_container)
        val_card.body_layout().addWidget(self.preview_scroll)
        root.addWidget(val_card)

        # ── Configurações ──
        conf_card = Card("Configurações de Restauro")
        conf_grid = QGridLayout()
        conf_grid.setSpacing(12)

        mode_panel = QFrame()
        mode_panel.setObjectName("Panel")
        mode_layout = QVBoxLayout(mode_panel)
        mode_layout.addWidget(QLabel("Modo de restauração"))
        self.mode_group = QButtonGroup(self)
        self.radio_all = QRadioButton("Restaurar tudo")
        self.radio_selection = QRadioButton("Restaurar seleção")
        self.radio_alternate = QRadioButton("Restaurar para outro local")
        self.radio_all.setChecked(True)
        for i, rb in enumerate((self.radio_all, self.radio_selection, self.radio_alternate)):
            self.mode_group.addButton(rb, i)
            mode_layout.addWidget(rb)
        self.mode_group.idClicked.connect(self._on_mode_changed)
        conf_grid.addWidget(mode_panel, 0, 0)

        conflict_panel = QFrame()
        conflict_panel.setObjectName("Panel")
        conflict_layout = QVBoxLayout(conflict_panel)
        conflict_layout.addWidget(QLabel("Políticas de Conflito"))
        self.conflict_group = QButtonGroup(self)
        self.radio_overwrite = QRadioButton("Sobrescrever")
        self.radio_ask = QRadioButton("Perguntar")
        self.radio_ignore = QRadioButton("Ignorar")
        self.radio_overwrite.setChecked(True)
        for i, rb in enumerate((self.radio_overwrite, self.radio_ask, self.radio_ignore)):
            self.conflict_group.addButton(rb, i)
            conflict_layout.addWidget(rb)
        conf_grid.addWidget(conflict_panel, 0, 1)

        conf_card.body_layout().addLayout(conf_grid)
        root.addWidget(conf_card)

        # ── Painéis dinâmicos ──
        self.frame_alt_dest = QFrame()
        alt_layout = QVBoxLayout(self.frame_alt_dest)
        alt_layout.setContentsMargins(0, 0, 0, 0)
        alt_layout.addWidget(QLabel("Pasta de destino alternativa"))
        alt_row = QHBoxLayout()
        self.alt_entry = QLineEdit()
        self.alt_entry.setPlaceholderText(r"Ex: D:\Recuperacao  ou  /mnt/recuperacao")
        btn_browse_alt = RestoreActionButton("Procurar")
        btn_browse_alt.clicked.connect(self._browse_alt_dest)
        alt_row.addWidget(self.alt_entry, 1)
        alt_row.addWidget(btn_browse_alt)
        alt_layout.addLayout(alt_row)
        root.addWidget(self.frame_alt_dest)
        self.frame_alt_dest.setVisible(False)

        self.frame_selection = QFrame()
        sel_layout = QVBoxLayout(self.frame_selection)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.addWidget(QLabel("Selecione quais pastas restaurar"))
        self.selection_list = QListWidget()
        self.selection_list.setMaximumHeight(140)
        sel_layout.addWidget(self.selection_list)
        root.addWidget(self.frame_selection)
        self.frame_selection.setVisible(False)

        # ── Status / progresso ──
        status_card = Card("Status da Restauração")
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

        self.progressbar = QProgressBar()
        self.progressbar.setObjectName("RestoreProgress")
        root.addWidget(self.progressbar)

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
        root.addWidget(log_card)

        btn_row = QHBoxLayout()
        self.btn_start = RestoreActionButton("Iniciar Restauração")
        self.btn_start.clicked.connect(self._start_restore)
        self.btn_stop = DangerButton("Cancelar Restauração")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_restore)
        btn_report = SecondaryButton("Abrir Relatório")
        btn_report.clicked.connect(lambda: open_path(self, self.state.last_restore_report_path))
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(btn_report)
        btn_row.addStretch(1)
        self.lbl_final_status = QLabel("")
        btn_row.addWidget(self.lbl_final_status)
        root.addLayout(btn_row)

    # ── modo de restauração ──
    def _on_mode_changed(self, _id: int):
        self.frame_alt_dest.setVisible(self.radio_alternate.isChecked())
        self.frame_selection.setVisible(self.radio_selection.isChecked())

    def _current_mode(self) -> str:
        if self.radio_selection.isChecked():
            return "selection"
        if self.radio_alternate.isChecked():
            return "alternate"
        return "all"

    def _current_conflict_mode(self) -> str:
        if self.radio_ask.isChecked():
            return "ask"
        if self.radio_ignore.isChecked():
            return "ignore"
        return "overwrite"

    # ── carregar backup ──
    def _browse_restore_src(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta do backup")
        if not path:
            return
        self.src_entry.setText(path)
        self._load_manifest(path)

    def _load_manifest(self, backup_dir: str):
        self.state.corporate_restore_plans = []
        self._clear_layout(self.preview_layout)
        try:
            plans = discover_corporate_restore_plans(backup_dir, domain=self.state.domain_netbios)
            if plans:
                self.state.restore_manifest = None
                self.state.corporate_restore_plans = [validate_corporate_restore_plan(p) for p in plans]
                total_files = sum(p.manifest.total_files for p in self.state.corporate_restore_plans)
                self.lbl_manifest_info.setText(
                    f"{icon_html('check', color=theme.SUCCESS)} backup corporativo carregado — "
                    f"{len(self.state.corporate_restore_plans)} usuários · {total_files} arquivos"
                )
                self.lbl_manifest_info.setStyleSheet("color: #22C55E;")
                self._populate_corporate_preview()
                return

            manifest = load_manifest(backup_dir)
            self.state.restore_manifest = manifest
            self.lbl_manifest_info.setText(
                f"{icon_html('check', color=theme.SUCCESS)} manifest.json carregado — {manifest.total_files} arquivos · "
                f"{self._human(manifest.total_size)} · backup de {manifest.backup_date[:10]} · "
                f"máquina: {manifest.machine}"
            )
            self.lbl_manifest_info.setStyleSheet("color: #22C55E;")
            self._populate_selection(manifest)
        except FileNotFoundError:
            self.state.restore_manifest = None
            self.lbl_manifest_info.setText("Backup não reconhecido. Selecione a pasta criada pelo BackupTool.")
            self.lbl_manifest_info.setStyleSheet("color: #EF4444;")
        except Exception as exc:
            self.state.restore_manifest = None
            self.lbl_manifest_info.setText(friendly_error(exc))
            self.lbl_manifest_info.setStyleSheet("color: #EF4444;")

    @staticmethod
    def _human(n):
        from core.scanner import human_size
        return human_size(n)

    def _clear_layout(self, layout):
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_corporate_preview(self):
        self._clear_layout(self.preview_layout)
        for plan in self.state.corporate_restore_plans:
            user = plan.manifest.user or os.path.basename(plan.user_dir)
            ok = not (plan.missing_files or plan.corrupted_files)
            status_icon = icon_html('check' if ok else 'warning', color=theme.SUCCESS if ok else theme.WARNING)
            text = (
                f"{status_icon} {user}<br>"
                f"Destino: {plan.destination}<br>"
                f"Arquivos: {plan.manifest.total_files} · "
                f"Ausentes: {plan.missing_files} · Corrompidos: {plan.corrupted_files}"
            )
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            self.preview_layout.insertWidget(self.preview_layout.count() - 1, lbl)
    def _populate_selection(self, manifest: Manifest):
        self.selection_list.clear()
        self._selection_items.clear()
        for root in get_manifest_roots(manifest):
            item = QListWidgetItem(root)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.selection_list.addItem(item)
            self._selection_items[root] = item

    def _browse_alt_dest(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar destino alternativo")
        if path:
            self.alt_entry.setText(path)

    # ── execução ──
    def _start_restore(self):
        if self.state.corporate_restore_plans:
            # Check admin privileges on Windows for corporate restore
            if platform.system() == "Windows" and is_admin and not is_admin():
                QMessageBox.critical(
                    self,
                    "Administrador necessário",
                    "A restauração corporativa precisa ser executada como Administrador para registrar os perfis corretamente no Windows."
                )
                return
            
            self._begin_common()
            self._worker = CorporateRestoreWorker(
                self.state.corporate_restore_plans, self._current_conflict_mode(), self.logs_dir,
                domain=self.state.domain_netbios,
            )
            self._worker.progress.connect(self._on_corporate_progress)
            self._worker.finished_ok.connect(self._on_corporate_finished)
            self._worker.failed.connect(self._on_failed)
            self._worker.confirm_conflict.connect(self._on_confirm_conflict)
            self._worker.start()
            return

        if self.state.restore_manifest is None:
            QMessageBox.critical(self, "Sem manifest", "Selecione uma pasta de backup válida antes de restaurar.")
            return

        mode = self._current_mode()
        conflict = self._current_conflict_mode()
        backup_dir = self.src_entry.text().strip()

        alternate = ""
        if mode == "alternate":
            alternate = self.alt_entry.text().strip()
            if not alternate:
                QMessageBox.critical(self, "Destino necessário", "Informe a pasta de destino alternativa.")
                return

        selection: list[str] = []
        if mode == "selection":
            selected_roots = [r for r, item in self._selection_items.items()
                               if item.checkState() == Qt.CheckState.Checked]
            if not selected_roots:
                QMessageBox.warning(self, "Nada selecionado", "Selecione ao menos uma pasta para restaurar.")
                return
            for entry in self.state.restore_manifest.files:
                for root in selected_roots:
                    if entry.source.startswith(root):
                        selection.append(entry.source)
                        break

        self._begin_common()
        self._worker = RestoreWorker(
            self.state.restore_manifest, backup_dir, mode, selection, alternate, conflict, self.logs_dir,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.confirm_conflict.connect(self._on_confirm_conflict)
        self._worker.start()

    def _begin_common(self):
        self._started_at = time.time()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_final_status.setText("")
        self.tile_user.set_value("Preparando...")
        self.tile_file.set_value("Preparando...")
        self.tile_time.set_value("0s · restante calculando...")
        self.progressbar.setValue(0)
        self.lbl_last_activity.setText("Iniciando restauração...")

    def _stop_restore(self):
        if self._worker:
            self._worker.request_stop()
        self.btn_stop.setEnabled(False)

    def _on_confirm_conflict(self, dest_path: str, container: dict):
        answer = QMessageBox.question(
            self, "Conflito", f"O arquivo já existe:\n{dest_path}\n\nSobrescrever?",
        )
        container["value"] = answer == QMessageBox.StandardButton.Yes
        container["event"].set()

    # ── progresso ──
    def _set_progress(self, done: int, total: int):
        pct = done / total if total else 0
        self.progressbar.setValue(int(pct * 100))
        self.lbl_counter.setText(f"Progresso: {done} / {total} arquivos")
        elapsed = format_duration(time.time() - self._started_at)
        remaining = estimate_remaining(self._started_at, done, total)
        self.tile_time.set_value(f"{elapsed} · restante {remaining}")

    def _on_progress(self, i, total, path):
        self._set_progress(i, total)
        self.tile_user.set_value("Backup manual")
        self.tile_file.set_value(short_path(path))
        line = f"[{i:>5}/{total}] {os.path.basename(path)}"
        self.lbl_last_activity.setText(line)
        self.log_message.emit(line + "\n")

    def _on_corporate_progress(self, user, i, total, path, done, overall_total):
        self._set_progress(done, overall_total)
        self.tile_user.set_value(user)
        self.tile_file.set_value(short_path(path))
        line = f"[{done:>5}/{overall_total}] {user}: {os.path.basename(path)}"
        self.lbl_last_activity.setText(line)
        self.log_message.emit(line + "\n")

    # ── finalização ──
    def _finish_common(self, result, json_path: str, csv_path: str, extra_lines: list[str]):
        self.progressbar.setValue(100)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.state.last_restore_report_path = json_path

        parts = [f"{icon_html('check', color=theme.SUCCESS)} {result.restored} restaurados"]
        if result.overwritten: parts.append(f"{result.overwritten} sobrescritos")
        if result.skipped: parts.append(f"{result.skipped} ignorados")
        if result.corrupted: parts.append(f"{result.corrupted} corrompidos")
        if result.errors: parts.append(f"{result.errors} erros")

        ok = (result.corrupted + result.errors) == 0
        msg = " · ".join(parts) + f" ({result.elapsed_seconds:.1f}s)"
        self.lbl_final_status.setStyleSheet(f"color: {'#22C55E' if ok else '#F59E0B'}; font-weight: 700;")
        self.lbl_final_status.setText(msg)
        self.lbl_last_activity.setText(msg)
        self.tile_time.set_value(f"{format_duration(result.elapsed_seconds)} · concluído")

        self.log_message.emit(f"\n{msg}\n")
        for line in extra_lines:
            self.log_message.emit(line + "\n")

        if result.corrupted:
            self.log_message.emit("\n── Arquivos corrompidos ──\n")
            for d in result.details:
                if d["status"] == "corrupted":
                    self.log_message.emit(f"  {d['source']}: {d['reason']}\n")
        if result.errors:
            self.log_message.emit("\n── Erros ──\n")
            for d in result.details:
                if d["status"] == "error":
                    self.log_message.emit(f"  {d['source']}: {d['reason']}\n")

        self.restore_finished.emit(ok)

    def _on_finished(self, result, json_path: str, csv_path: str):
        extra = [f"Relatório JSON : {json_path}", f"Relatório CSV  : {csv_path}"]
        self._finish_common(result, json_path, csv_path, extra)

    def _on_corporate_finished(self, result, json_path: str, csv_path: str):
        extra = [f"Relatório JSON : {json_path}", f"Relatório CSV  : {csv_path}"]
        for item in result.user_results:
            extra.append(
                f"  {item['user']} → {item['destination']}: "
                f"{item['result'].restored} restaurados, "
                f"{item['result'].corrupted} corrompidos, "
                f"{item['result'].errors} erros"
            )
        self._finish_common(result, json_path, csv_path, extra)

    def _on_failed(self, message: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        QMessageBox.critical(self, "Erro durante a restauração", friendly_error(message))
