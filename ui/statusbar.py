"""
ui/statusbar.py — Barra de status inferior.

Equivalente ao `_build_status_bar` da versão CustomTkinter: mensagem de
status à esquerda (ocupa o espaço disponível) e versão/SO fixos à direita.
"""

from __future__ import annotations

import platform

from PySide6.QtWidgets import QStatusBar, QLabel

APP_VERSION = "2.1"


class AppStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeGripEnabled(False)

        self._status_label = QLabel("Status: pronto")
        self.addWidget(self._status_label, 1)

        version_label = QLabel(f"BackupTool Professional {APP_VERSION} · {platform.system()}")
        version_label.setObjectName("Muted")
        self.addPermanentWidget(version_label)

    def set_status(self, text: str):
        self._status_label.setText(f"Status: {text}")
