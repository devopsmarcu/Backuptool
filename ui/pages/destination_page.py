"""
ui/pages/destination_page.py — Aba "3 · Destino".

Porta de `_build_tab_destino` / `_refresh_drives` / `_select_drive` /
`_browse_dest`. Usa `core.destinations.detect_external_drives` exatamente
como antes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel, QLineEdit, QFileDialog,
)

from core.destinations import detect_external_drives
from styles import dark_theme as theme
from styles.icons import icon_drive, icon_refresh, icon_folder
from styles.svg_icons import icon_html
from ui.state import AppState
from ui.widgets import Card, SectionIntro, PrimaryButton, SecondaryButton, EmptyState


class DestinationPage(QWidget):
    destination_changed = Signal(str)

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Destino do backup",
            "Use um dispositivo detectado ou selecione uma pasta de rede/local com espaço suficiente.",
        ))

        drives_card = Card("Dispositivos Detectados")
        self.drives_scroll = QScrollArea()
        self.drives_scroll.setWidgetResizable(True)
        self.drives_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.drives_container = QWidget()
        self.drives_layout = QVBoxLayout(self.drives_container)
        self.drives_layout.setSpacing(6)
        self.drives_layout.addStretch(1)
        self.drives_scroll.setWidget(self.drives_container)
        self.drives_scroll.setMinimumHeight(140)
        drives_card.body_layout().addWidget(self.drives_scroll)

        refresh_row = QHBoxLayout()
        btn_refresh = SecondaryButton("Atualizar dispositivos")
        btn_refresh.setIcon(icon_refresh(self))
        btn_refresh.clicked.connect(self.refresh_drives)
        refresh_row.addWidget(btn_refresh)
        refresh_row.addStretch(1)
        drives_card.body_layout().addLayout(refresh_row)
        root.addWidget(drives_card)

        manual_card = Card("Seleção Manual")
        input_row = QHBoxLayout()
        self.dest_entry = QLineEdit()
        self.dest_entry.setPlaceholderText(r"Ex: \\servidor\backup  ou  /mnt/externo")
        self.dest_entry.textChanged.connect(self._on_text_changed)
        btn_browse = PrimaryButton("Procurar")
        btn_browse.setIcon(icon_folder(self))
        btn_browse.clicked.connect(self._browse_dest)
        input_row.addWidget(self.dest_entry, 1)
        input_row.addWidget(btn_browse)
        manual_card.body_layout().addLayout(input_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("Muted")
        manual_card.body_layout().addWidget(self.lbl_status)
        root.addWidget(manual_card)
        root.addStretch(1)

        self.refresh_drives()

    def current_destination(self) -> str:
        return self.dest_entry.text().strip()

    def _on_text_changed(self, text: str):
        self.state.destination = text.strip()
        self.destination_changed.emit(text)

    def refresh_drives(self):
        while self.drives_layout.count() > 1:
            item = self.drives_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        drives = detect_external_drives()
        if not drives:
            empty = EmptyState("disc", "Nenhum dispositivo detectado",
                               "Tente conectar um HD externo ou mapear uma unidade de rede.")
            self.drives_layout.insertWidget(0, empty)
            return

        for d in drives:
            row = QFrame()
            row.setObjectName("Panel")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            icon_lbl = QLabel()
            icon_lbl.setPixmap(icon_drive(self).pixmap(20, 20))
            text_lbl = QLabel(f"{d['label']}  [{d['type']}]  —  {d['path']}")
            btn_use = PrimaryButton("Usar")
            btn_use.setFixedWidth(90)
            btn_use.clicked.connect(lambda _checked, path=d["path"]: self._select_drive(path))
            row_layout.addWidget(icon_lbl)
            row_layout.addWidget(text_lbl, 1)
            row_layout.addWidget(btn_use)
            self.drives_layout.insertWidget(self.drives_layout.count() - 1, row)

    def _select_drive(self, path: str):
        self.dest_entry.setText(path)
        self.lbl_status.setText(f"{icon_html('check', color=theme.SUCCESS)} Selecionado: {path}")
        self.lbl_status.setStyleSheet(f"color: {theme.SUCCESS};")

    def _browse_dest(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar destino")
        if path:
            self.dest_entry.setText(path)
