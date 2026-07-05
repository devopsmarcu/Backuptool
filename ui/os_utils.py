"""
ui/os_utils.py — Utilitário de SO usado pelas páginas de execução.

Porta de `_open_path` (BackupApp, CustomTkinter): abre uma pasta/arquivo
no explorador de arquivos nativo do sistema operacional.
"""

from __future__ import annotations

import os
import platform
import subprocess

from PySide6.QtWidgets import QMessageBox, QWidget

from ui.format_utils import friendly_error


def open_path(parent: QWidget, path: str):
    if not path:
        QMessageBox.information(parent, "Nada para abrir", "Nenhum relatório ou pasta disponível ainda.")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        QMessageBox.critical(parent, "Não foi possível abrir", friendly_error(exc))
