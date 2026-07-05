"""
ui/pages/logs_page.py — Seção "Logs" do menu principal.

Antes, os logs de backup e restauração ficavam embutidos nas próprias
abas "5 · Backup" e "6 · Restaurar" (CTkTextbox). Para seguir a
referência visual (menu "Logs" dedicado), eles foram centralizados
aqui: `BackupPage`/`RestorePage` emitem o sinal `log_message`, e o
`MainWindow` encaminha cada linha para o painel correspondente.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPlainTextEdit

from ui.widgets import Card, SectionIntro, SecondaryButton, GhostButton


class LogsPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(SectionIntro(
            "Logs de execução",
            "Acompanhe, em tempo real, tudo o que acontece durante o backup e a restauração.",
        ), 1)
        btn_back = GhostButton("← Voltar para o Backup")
        btn_back.clicked.connect(self.back_requested)
        header_row.addWidget(btn_back, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.backup_log = self._build_log_panel(splitter, "Log de Backup")
        self.restore_log = self._build_log_panel(splitter, "Log de Restauração")

        root.addWidget(splitter, 1)

    def _build_log_panel(self, parent_splitter: QSplitter, title: str) -> QPlainTextEdit:
        card = Card(title)
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMinimumWidth(320)
        card.body_layout().addWidget(text_edit, 1)

        btn_clear = SecondaryButton("Limpar")
        btn_clear.clicked.connect(text_edit.clear)
        card.body_layout().addWidget(btn_clear, 0, Qt.AlignmentFlag.AlignLeft)

        parent_splitter.addWidget(card)
        return text_edit

    def append_backup_log(self, text: str):
        self.backup_log.moveCursor(self.backup_log.textCursor().MoveOperation.End)
        self.backup_log.insertPlainText(text)
        self.backup_log.moveCursor(self.backup_log.textCursor().MoveOperation.End)

    def append_restore_log(self, text: str):
        self.restore_log.moveCursor(self.restore_log.textCursor().MoveOperation.End)
        self.restore_log.insertPlainText(text)
        self.restore_log.moveCursor(self.restore_log.textCursor().MoveOperation.End)

    def clear_all(self):
        self.backup_log.clear()
        self.restore_log.clear()
