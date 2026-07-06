from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from styles.dark_theme import build_stylesheet
from ui.main_window import MainWindow

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BackupTool")
    app.setOrganizationName("Santa Casa da Bahia")

    # Global Font Setup
    font = QFont("Inter", 10)
    app.setFont(font)

    # "Fusion" é a base de estilo Qt mais previsível entre Windows e Linux
    # para QSS customizado (bordas arredondadas, cores) — os estilos nativos
    # (ex.: "windowsvista") ignoram parte do QSS aplicado aqui.
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    window = MainWindow(PROJECT_ROOT)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
