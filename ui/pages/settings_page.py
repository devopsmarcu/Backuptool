"""
ui/pages/settings_page.py — Seção "Configurações" do menu principal.

Reúne o que antes era a parte "Exclusões Aplicadas" da aba "2 · Origem"
(CustomTkinter) mais o nome do técnico usado nos relatórios
(`state.technician`, antes fixo via `socket.gethostname()`, agora
editável). Nenhuma regra de negócio nova: `state.exclusions` /
`state.excl_exts` / `state.technician` são os mesmos atributos lidos
por `core.scanner` e `core.report`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QMessageBox

from ui.state import AppState
from ui.widgets import Card, SectionIntro, PrimaryButton, GhostButton


class SettingsPage(QWidget):
    back_requested = Signal()

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(SectionIntro(
            "Configurações",
            "Pastas/padrões e extensões ignorados durante o scan, e dados usados nos relatórios.",
        ), 1)
        btn_back = GhostButton("← Voltar para o Backup")
        btn_back.clicked.connect(self.back_requested)
        header_row.addWidget(btn_back, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header_row)

        excl_card = Card("Exclusões Aplicadas (pastas / padrões)")
        excl_card.body_layout().addWidget(QLabel("Um item por linha."))
        self.excl_text = QPlainTextEdit()
        self.excl_text.setPlainText("\n".join(self.state.exclusions))
        excl_card.body_layout().addWidget(self.excl_text)
        root.addWidget(excl_card, 1)

        ext_card = Card("Extensões Excluídas")
        ext_card.body_layout().addWidget(QLabel("Uma extensão por linha (ex.: .tmp)."))
        self.ext_text = QPlainTextEdit()
        self.ext_text.setPlainText("\n".join(self.state.excl_exts))
        ext_card.body_layout().addWidget(self.ext_text)
        root.addWidget(ext_card, 1)

        session_card = Card("Sessão")
        session_row = QHBoxLayout()
        session_row.addWidget(QLabel("Técnico / máquina responsável:"))
        self.technician_entry = QLineEdit(self.state.technician)
        session_row.addWidget(self.technician_entry, 1)
        session_card.body_layout().addLayout(session_row)
        root.addWidget(session_card)

        btn_save = PrimaryButton("Salvar alterações")
        btn_save.clicked.connect(self._save)
        root.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignLeft)

    def _save(self):
        self.state.exclusions = [l.strip() for l in self.excl_text.toPlainText().splitlines() if l.strip()]
        self.state.excl_exts = [l.strip() for l in self.ext_text.toPlainText().splitlines() if l.strip()]
        self.state.technician = self.technician_entry.text().strip() or self.state.technician
        QMessageBox.information(self, "Configurações", "Alterações salvas com sucesso.")
