from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from styles.dark_theme import build_stylesheet
from styles.icons import app_icon
from ui.main_window import MainWindow

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BackupTool")
    app.setOrganizationName("Santa Casa da Bahia")

    # Ícone da aplicação: usado na barra de título, na barra de tarefas do
    # Windows e como ícone do executável. Sem isso, o SO mostra um ícone
    # genérico mesmo com resources/icons/icon.ico presente no projeto.
    app.setWindowIcon(app_icon())

    # Global Font Setup
    font = QFont("Inter", 10)
    app.setFont(font)

    # "Fusion" é a base de estilo Qt mais previsível entre Windows e Linux
    # para QSS customizado (bordas arredondadas, cores) — os estilos nativos
    # (ex.: "windowsvista") ignoram parte do QSS aplicado aqui.
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    window = MainWindow(PROJECT_ROOT)
    window.setWindowIcon(app_icon())
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
