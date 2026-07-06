"""
ui/main_window.py — Janela principal do BackupTool (PySide6).

Substitui a classe `BackupApp` (CustomTkinter) como orquestrador da UI.
Não implementa nenhuma regra de negócio: apenas monta o layout (cabeçalho
+ stepper + páginas + rodapé + status bar), conecta os sinais das
páginas entre si e mantém o `AppState` compartilhado.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
)

from styles.icons import app_icon, icon_back, icon_forward, icon_refresh
from ui.state import AppState
from ui.toolbar import HeaderBar
from ui.navigation import Stepper
from ui.statusbar import AppStatusBar
from ui.widgets import SecondaryButton, PrimaryButton, GhostButton

from ui.pages.users_page import UsersPage
from ui.pages.source_page import SourcePage
from ui.pages.destination_page import DestinationPage
from ui.pages.summary_page import SummaryPage
from ui.pages.backup_page import BackupPage
from ui.pages.restore_page import RestorePage
from ui.pages.logs_page import LogsPage
from ui.pages.settings_page import SettingsPage

STEP_LABELS = ["Usuários", "Origem", "Destino", "Resumo", "Backup", "Restaurar"]
STEP_DESCRIPTIONS = [
    "Escolho quais perfis entram no backup.",
    "Revise pastas padrão, pastas extras e exclusões.",
    "Selecione onde o backup será salvo.",
    "Confira usuários, arquivos, tamanho e destino antes de iniciar.",
    "Acompanhe a execução em tempo real.",
    "Valide um backup e restaure usuários para o destino corporativo.",
]

TOP_WIZARD, TOP_LOGS, TOP_SETTINGS = 0, 1, 2


class MainWindow(QMainWindow):
    def __init__(self, project_root: str, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.logs_dir = os.path.join(project_root, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)

        self.state = AppState()

        self.setWindowTitle("BackupTool")
        self.setWindowIcon(app_icon())
        self._configure_window()

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Cabeçalho ──
        self.header = HeaderBar("BackupTool")
        self.header.section_changed.connect(self._on_section_changed)
        outer.addWidget(self.header)

        # ── Stepper ──
        self.stepper = Stepper(STEP_LABELS)
        self.stepper.step_requested.connect(self._jump_to_step)
        stepper_wrap = QWidget()
        stepper_layout = QHBoxLayout(stepper_wrap)
        stepper_layout.setContentsMargins(20, 14, 20, 6)
        stepper_layout.addWidget(self.stepper)
        outer.addWidget(stepper_wrap)
        self.stepper_wrap = stepper_wrap

        # ── Conteúdo (wizard | logs | configurações) ──
        self.top_stack = QStackedWidget()
        outer.addWidget(self.top_stack, 1)

        self._build_wizard()
        self._build_logs_and_settings()

        # ── Rodapé de navegação do assistente ──
        self.footer = self._build_footer()
        outer.addWidget(self.footer)

        # ── Barra de status ──
        self.statusbar = AppStatusBar()
        self.setStatusBar(self.statusbar)

        self._wire_cross_page_signals()
        self._on_wizard_step_changed(0)

    # ══════════════════════════════════════════
    #  Layout
    # ══════════════════════════════════════════

    def _configure_window(self):
        screen = QGuiApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None
        screen_w = geo.width() if geo else 1600
        screen_h = geo.height() if geo else 900

        if screen_w >= 3840:
            target_w, target_h = 1800, 1000
        elif screen_w >= 1920:
            target_w, target_h = 1600, 900
        elif screen_w >= 1366:
            target_w, target_h = 1200, 700
        else:
            target_w, target_h = 1000, 620

        margin_w = 80 if screen_w >= 1600 else 40
        margin_h = 80 if screen_h >= 900 else 48

        width = min(target_w, max(900, screen_w - margin_w))
        height = min(target_h, max(620, screen_h - margin_h))

        self.resize(width, height)
        self.setMinimumSize(min(900, screen_w), min(620, screen_h))

    def _build_wizard(self):
        wizard_widget = QWidget()
        layout = QVBoxLayout(wizard_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.wizard_stack = QStackedWidget()
        layout.addWidget(self.wizard_stack)

        self.users_page = UsersPage(self.state)
        self.source_page = SourcePage(self.state)
        self.destination_page = DestinationPage(self.state)
        self.summary_page = SummaryPage(self.state, self.logs_dir)
        self.backup_page = BackupPage(self.state, self.logs_dir)
        self.restore_page = RestorePage(self.state, self.logs_dir)

        for page in (
            self.users_page, self.source_page, self.destination_page,
            self.summary_page, self.backup_page, self.restore_page,
        ):
            self.wizard_stack.addWidget(page)

        self.top_stack.addWidget(wizard_widget)  # index TOP_WIZARD

    def _build_logs_and_settings(self):
        self._last_wizard_index = 0

        self.logs_page = LogsPage()
        self.logs_page.back_requested.connect(self._return_to_wizard)
        self.top_stack.addWidget(self.logs_page)  # index TOP_LOGS

        self.settings_page = SettingsPage(self.state)
        self.settings_page.back_requested.connect(self._return_to_wizard)
        self.top_stack.addWidget(self.settings_page)  # index TOP_SETTINGS

    def _return_to_wizard(self):
        """Volta exatamente para a etapa do assistente em que o usuário
        estava antes de abrir Logs/Configurações (em vez de sempre voltar
        à etapa 1)."""
        self.header.set_active_section("restore" if self._last_wizard_index == 5 else "backup")
        self._set_wizard_index(self._last_wizard_index)

    def _build_footer(self) -> QWidget:
        foot = QWidget()
        foot.setObjectName("HeaderBar")  # reaproveita o estilo do cabeçalho (fundo + borda)
        row = QHBoxLayout(foot)
        row.setContentsMargins(20, 10, 20, 10)

        self.btn_back = SecondaryButton("Voltar")
        self.btn_back.setIcon(icon_back(self))
        self.btn_back.clicked.connect(self._go_back)

        self.btn_restart = SecondaryButton("Reiniciar Processo")
        self.btn_restart.setIcon(icon_refresh(self))
        self.btn_restart.clicked.connect(self._restart_process)

        self.btn_next = PrimaryButton("Próximo")
        self.btn_next.setIcon(icon_forward(self))
        self.btn_next.clicked.connect(self._go_next)

        row.addWidget(self.btn_back)
        row.addWidget(self.btn_restart)
        row.addStretch(1)
        row.addWidget(self.btn_next)
        return foot

    # ══════════════════════════════════════════
    #  Sinais entre páginas
    # ══════════════════════════════════════════

    def _wire_cross_page_signals(self):
        self.backup_page.log_message.connect(self.logs_page.append_backup_log)
        self.restore_page.log_message.connect(self.logs_page.append_restore_log)
        self.backup_page.open_logs_requested.connect(lambda: self._activate_section("logs"))
        self.restore_page.open_logs_requested.connect(lambda: self._activate_section("logs"))

        self.backup_page.backup_finished.connect(
            lambda ok: self.statusbar.set_status("Backup concluído." if ok else "Backup concluído com erros.")
        )
        self.restore_page.restore_finished.connect(
            lambda ok: self.statusbar.set_status("Restauração concluída." if ok else "Restauração concluída com avisos.")
        )
        self.summary_page.scan_completed.connect(lambda: self.statusbar.set_status("Scan concluído. Resumo atualizado."))

    # ══════════════════════════════════════════
    #  Navegação — menu principal
    # ══════════════════════════════════════════

    def _on_section_changed(self, key: str):
        self._activate_section(key, update_header=False)

    def _activate_section(self, key: str, update_header: bool = True):
        if update_header:
            self.header.set_active_section(key)

        if key == "logs":
            if self.top_stack.currentIndex() == TOP_WIZARD:
                self._last_wizard_index = self.wizard_stack.currentIndex()
            self.top_stack.setCurrentIndex(TOP_LOGS)
            self.stepper_wrap.setVisible(False)
            self.footer.setVisible(False)
        elif key == "settings":
            if self.top_stack.currentIndex() == TOP_WIZARD:
                self._last_wizard_index = self.wizard_stack.currentIndex()
            self.top_stack.setCurrentIndex(TOP_SETTINGS)
            self.stepper_wrap.setVisible(False)
            self.footer.setVisible(False)
        else:
            self.top_stack.setCurrentIndex(TOP_WIZARD)
            self.stepper_wrap.setVisible(True)
            self.footer.setVisible(True)
            current = self.wizard_stack.currentIndex()
            if key == "restore" and current != 5:
                self._set_wizard_index(5)
            elif key == "backup" and current == 5:
                self._set_wizard_index(0)

    # ══════════════════════════════════════════
    #  Navegação — assistente (stepper / Voltar / Próximo)
    # ══════════════════════════════════════════

    def _jump_to_step(self, index: int):
        self._set_wizard_index(index)

    def _go_next(self):
        idx = self.wizard_stack.currentIndex()
        if idx < len(STEP_LABELS) - 1:
            self._set_wizard_index(idx + 1)

    def _go_back(self):
        idx = self.wizard_stack.currentIndex()
        if idx > 0:
            self._set_wizard_index(idx - 1)

    def _set_wizard_index(self, index: int):
        self.wizard_stack.setCurrentIndex(index)
        self.top_stack.setCurrentIndex(TOP_WIZARD)
        self.stepper_wrap.setVisible(True)
        self.footer.setVisible(True)
        self._on_wizard_step_changed(index)

    def _on_wizard_step_changed(self, index: int):
        self.stepper.set_current_index(index)
        self.btn_back.setEnabled(index > 0)
        self.btn_next.setEnabled(index < len(STEP_LABELS) - 1)
        self.header.set_active_section("restore" if index == 5 else "backup")
        self.header.set_session_info(
            f"Etapa {index + 1} de {len(STEP_LABELS)}",
            f"{STEP_DESCRIPTIONS[index]}\nMáquina: {self.state.technician}",
        )
        self.statusbar.set_status(STEP_DESCRIPTIONS[index])

    # ══════════════════════════════════════════
    #  Reiniciar processo
    # ══════════════════════════════════════════

    def _restart_process(self):
        if self.backup_page._worker and self.backup_page._worker.isRunning():
            self.backup_page._worker.request_stop()
        if self.restore_page._worker and self.restore_page._worker.isRunning():
            self.restore_page._worker.request_stop()

        self.state.reset_for_new_run()

        self.destination_page.dest_entry.clear()
        self.destination_page.lbl_status.setText("")

        self.backup_page.progressbar.setValue(0)
        self.backup_page.lbl_percentage.setText("0%")
        self.backup_page.lbl_counter.setText("Progresso: 0 / 0 arquivos")
        self.backup_page.lbl_final_status.setText("")
        self.backup_page.lbl_last_activity.setText("Nenhuma atividade ainda.")
        self.backup_page.btn_start.setEnabled(True)
        self.backup_page.btn_stop.setEnabled(False)

        self.restore_page.progressbar.setValue(0)
        self.restore_page.lbl_counter.setText("Progresso: 0 / 0 arquivos")
        self.restore_page.lbl_final_status.setText("")
        self.restore_page.lbl_last_activity.setText("Nenhuma atividade ainda.")
        self.restore_page.src_entry.clear()
        self.restore_page.lbl_manifest_info.setText("")
        self.restore_page.btn_start.setEnabled(True)
        self.restore_page.btn_stop.setEnabled(False)

        self.logs_page.clear_all()

        self._set_wizard_index(0)
        self.header.set_active_section("backup")
