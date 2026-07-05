"""
ui/toolbar.py — Barra superior (cabeçalho) do BackupTool.

Contém: logotipo + nome do app, o menu principal (Backup / Restauração /
Logs / Configurações) e o painel de informações da sessão (etapa atual,
usuário/máquina), conforme a referência visual enviada.

É um QFrame simples (não um QToolBar/QMenuBar nativo) porque o layout
pedido — abas de texto sublinhadas ao estilo "segmented" — é mais fácil
de reproduzir fielmente assim, mas o comportamento (seleção exclusiva,
sinal ao trocar de seção) é o mesmo que se esperaria de um menu principal.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QSizePolicy,
)

from styles.icons import app_logo_pixmap

SECTIONS = [
    ("backup", "Backup"),
    ("restore", "Restauração"),
    ("logs", "Logs"),
    ("settings", "Configurações"),
]


class HeaderBar(QFrame):
    section_changed = Signal(str)

    def __init__(self, app_name: str = "BackupTool", parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(24)

        # ── Logo + nome ──
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(app_logo_pixmap(34))
        title = QLabel(app_name)
        title.setObjectName("AppTitle")
        brand.addWidget(logo)
        brand.addWidget(title)
        brand_widget = QFrame()
        brand_widget.setLayout(brand)
        layout.addWidget(brand_widget)

        layout.addStretch(1)

        # ── Menu principal ──
        nav = QHBoxLayout()
        nav.setSpacing(4)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, label in SECTIONS:
            btn = QPushButton(label)
            btn.setObjectName("NavTab")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, k=key: self.section_changed.emit(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            nav.addWidget(btn)
        self._buttons["backup"].setChecked(True)
        nav_widget = QFrame()
        nav_widget.setLayout(nav)
        layout.addWidget(nav_widget)

        layout.addStretch(1)

        # ── Informações da sessão ──
        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        info_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_info_title = QLabel("Etapa 1 de 6")
        self.lbl_info_title.setObjectName("SessionInfoTitle")
        self.lbl_info_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_info_sub = QLabel("")
        self.lbl_info_sub.setObjectName("SessionInfoSub")
        self.lbl_info_sub.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_info_sub.setWordWrap(True)
        self.lbl_info_sub.setMaximumWidth(320)
        info_box.addWidget(self.lbl_info_title)
        info_box.addWidget(self.lbl_info_sub)
        info_widget = QFrame()
        info_widget.setLayout(info_box)
        info_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        layout.addWidget(info_widget)

    def set_active_section(self, key: str):
        btn = self._buttons.get(key)
        if btn:
            btn.setChecked(True)

    def set_session_info(self, title: str, subtitle: str):
        self.lbl_info_title.setText(title)
        self.lbl_info_sub.setText(subtitle)
