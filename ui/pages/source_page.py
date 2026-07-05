"""
ui/pages/source_page.py — Aba "2 · Origem".

Porta de `_build_tab_origem` / `_refresh_paths_list` / `_add_path` /
`_remove_path`. As exclusões (pastas/extensões ignoradas) foram
reorganizadas para a nova página "Configurações" — a lista em si
(`state.exclusions` / `state.excl_exts`) continua sendo a mesma usada
pelo scan, apenas o local de edição na UI mudou.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QFileDialog, QLabel,
)

from styles.icons import icon_folder, icon_add, icon_remove
from ui.state import AppState
from ui.widgets import Card, SectionIntro, PrimaryButton, DangerButton


class SourcePage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Origens do backup",
            "Revise as pastas padrão e adicione locais extras somente quando necessário. "
            "As exclusões aplicadas podem ser ajustadas em Configurações.",
        ))

        card = Card("Pastas de Origem")
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        card.body_layout().addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_add = PrimaryButton("Adicionar pasta")
        btn_add.setIcon(icon_add(self))
        btn_add.clicked.connect(self._add_path)
        btn_remove = DangerButton("Remover selecionada")
        btn_remove.setIcon(icon_remove(self))
        btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addStretch(1)
        card.body_layout().addLayout(btn_row)

        root.addWidget(card, 1)
        root.addStretch(0)

        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for path in self.state.paths:
            item = QListWidgetItem(icon_folder(self), path)
            self.list_widget.addItem(item)

    def _add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta")
        if path and path not in self.state.paths:
            self.state.paths.append(path)
            self._refresh_list()

    def _remove_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        path = item.text()
        if path in self.state.paths:
            self.state.paths.remove(path)
        self._refresh_list()
