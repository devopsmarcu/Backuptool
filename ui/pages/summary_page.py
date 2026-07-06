"""
ui/pages/summary_page.py — Aba "4 · Resumo".

Porta de `_build_tab_resumo` / `_start_scan` / `_scan_thread` / `_set_resumo`.
O scan roda em `ui.workers.ScanWorker` (QThread) em vez de
`threading.Thread` + `self.after(...)`, mas chama exatamente as mesmas
funções de `core.scanner`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QMessageBox

from core.destinations import validate_destination
from ui.state import AppState
from ui.widgets import SummaryStatCard, SectionIntro, PrimaryButton
from ui.workers import ScanWorker

WAITING_TEXT = "Aguardando scan..."


class SummaryPage(QWidget):
    scan_completed = Signal()

    def __init__(self, state: AppState, logs_dir: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.logs_dir = logs_dir
        self._worker: ScanWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Resumo e validação",
            "Confira usuários, arquivos, tamanho estimado, destino e exclusões antes de executar.",
        ))

        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(12)
        root.addWidget(self.grid_container, 1)

        self.cards: dict[str, SummaryStatCard] = {}
        self.labels: dict[str, QLabel] = {}

        # Mapeamento de Ícones para cada card de resumo
        card_configs = [
            ("dest", "Destino", "📂"),
            ("stats", "Estatísticas", "📊"),
            ("users", "Usuários", "👤"),
            ("excl", "Exclusões", "🚫"),
        ]

        for key, title, icon in card_configs:
            card = SummaryStatCard(icon, title)
            # A SummaryStatCard já cria o label interno, vamos capturá-lo para atualizar o texto
            # Como o label está no layout, precisamos de uma forma de acessá-lo.
            # Vamos adicionar um método `set_value` ao SummaryStatCard (já fizemos no Write anterior).
            self.cards[key] = card
            # Para manter compatibilidade com o código de atualização,
            # vamos simular a existência de `self.labels` ou atualizar a lógica de update.
            # No código original, self.labels[key] era usado.
            # Vamos criar um mock ou mudar a função de update.
            self.labels[key] = None # Placeholder, usaremos card.set_value()

        self._arrange_grid(4)

        self.btn_scan = PrimaryButton("Validar e gerar resumo")
        self.btn_scan.clicked.connect(self._start_scan)
        root.addWidget(self.btn_scan, 0, Qt.AlignmentFlag.AlignLeft)

    def _arrange_grid(self, columns: int):
        for key in self.cards:
            self.grid.removeWidget(self.cards[key])
        for i in range(4):
            self.grid.setColumnStretch(i, 1 if i < columns else 0)
        order = ["dest", "stats", "users", "excl"]
        for i, key in enumerate(order):
            row, col = divmod(i, columns)
            self.grid.addWidget(self.cards[key], row, col)

    def resizeEvent(self, event):
        width = self.width()
        if width < 640:
            self._arrange_grid(1)
        elif width < 1000:
            self._arrange_grid(2)
        else:
            self._arrange_grid(4)
        super().resizeEvent(event)

    # ── scan ──
    def _start_scan(self):
        destination = self.state.destination.strip()
        valid, msg = validate_destination(destination)
        if not valid:
            QMessageBox.critical(self, "Destino inválido", msg)
            return

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Escaneando...")
        self.cards["stats"].set_value(
            "Preparando resumo. A varredura pode levar alguns minutos em perfis grandes."
        )

        self._worker = ScanWorker(
            self.state.paths, self.state.exclusions, self.state.excl_exts,
            self.state.selected_profiles, destination,
        )
        self._worker.files_found.connect(self._on_files_found)
        self._worker.finished_ok.connect(self._on_scan_finished)
        self._worker.failed.connect(self._on_scan_failed)
        self._worker.start()

    def _on_files_found(self, count: int):
        self.cards["stats"].set_value(
            f"Varredura em andamento\n\nArquivos encontrados: {count}\nA interface continua ativa."
        )

    def _on_scan_finished(self, data: dict):
        self.state.scanned = data["scanned"]
        self.state.scanned_by_user = data["scanned_by_user"]
        self.cards["dest"].set_value(data["dest_text"])
        self.cards["stats"].set_value(data["stats_text"])
        self.cards["users"].set_value(data["users_text"])
        self.cards["excl"].set_value(data["excl_text"])
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Atualizar resumo")
        self.scan_completed.emit()

    def _on_scan_failed(self, message: str):
        QMessageBox.critical(self, "Erro durante o scan", message)
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Atualizar resumo")
