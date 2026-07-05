"""
main.py — BackupTool GUI (PySide6)

Ponto de entrada da aplicação migrada de CustomTkinter para PySide6.
Nenhuma lógica de negócio vive aqui — apenas inicialização do
QApplication, aplicação do tema escuro e exibição da MainWindow.

Estrutura (ver instruções de migração):
  ui/            → janela principal, cabeçalho, stepper, status bar, páginas
  styles/        → paleta de cores + QSS + ícones
  core/, config/ → módulos de negócio já existentes no projeto (inalterados)
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from styles.dark_theme import build_stylesheet
from ui.main_window import MainWindow

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BackupTool")
    app.setOrganizationName("Santa Casa da Bahia")
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
