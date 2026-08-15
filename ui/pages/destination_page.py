"""
ui/pages/destination_page.py — Aba "3 · Destino".

Porta de `_build_tab_destino` / `_refresh_drives` / `_select_drive` /
`_browse_dest`. Usa `core.destinations.detect_external_drives` exatamente
como antes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame, QLabel, QLineEdit,
    QFileDialog, QCheckBox, QSpinBox, QMessageBox,
)

from core.destinations import detect_external_drives
from styles import dark_theme as theme
from styles.svg_icons import icon_html, icon_drive, icon_refresh, icon_folder
from ui.state import AppState
from ui.widgets import Card, SectionIntro, PrimaryButton, SecondaryButton, EmptyState
from ui.workers import SftpTestWorker


class DestinationPage(QWidget):
    destination_changed = Signal(str)

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
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
        btn_refresh.setIcon(icon_refresh())
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
        btn_browse.setIcon(icon_folder())
        btn_browse.clicked.connect(self._browse_dest)
        input_row.addWidget(self.dest_entry, 1)
        input_row.addWidget(btn_browse)
        manual_card.body_layout().addLayout(input_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("Muted")
        manual_card.body_layout().addWidget(self.lbl_status)
        root.addWidget(manual_card)

        # ── Envio remoto via SFTP (opcional, executado após o backup local) ──
        sftp_card = Card("Envio remoto via SFTP (opcional)")
        sftp_card.body_layout().addWidget(QLabel(
            "O backup sempre é gravado primeiro no destino local/de rede acima. "
            "Se preenchido, ele também é enviado para um servidor remoto via SFTP "
            "logo após a conclusão."
        ))

        self.chk_sftp_enabled = QCheckBox("Enviar backup por SFTP após a conclusão")
        self.chk_sftp_enabled.setChecked(self.state.sftp_enabled)
        self.chk_sftp_enabled.toggled.connect(self._on_sftp_toggled)
        sftp_card.body_layout().addWidget(self.chk_sftp_enabled)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        grid.addWidget(QLabel("Host:"), 0, 0)
        self.sftp_host_entry = QLineEdit(self.state.sftp_host)
        self.sftp_host_entry.setPlaceholderText("ex.: backup.empresa.local")
        grid.addWidget(self.sftp_host_entry, 0, 1)

        grid.addWidget(QLabel("Porta:"), 0, 2)
        self.sftp_port_spin = QSpinBox()
        self.sftp_port_spin.setRange(1, 65535)
        self.sftp_port_spin.setValue(self.state.sftp_port or 22)
        grid.addWidget(self.sftp_port_spin, 0, 3)

        grid.addWidget(QLabel("Usuário:"), 1, 0)
        self.sftp_user_entry = QLineEdit(self.state.sftp_username)
        grid.addWidget(self.sftp_user_entry, 1, 1)

        grid.addWidget(QLabel("Senha:"), 1, 2)
        self.sftp_password_entry = QLineEdit(self.state.sftp_password)
        self.sftp_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self.sftp_password_entry, 1, 3)

        grid.addWidget(QLabel("Chave privada (opcional):"), 2, 0)
        key_row = QHBoxLayout()
        self.sftp_key_entry = QLineEdit(self.state.sftp_private_key_path)
        self.sftp_key_entry.setPlaceholderText("Deixe vazio para usar usuário/senha")
        btn_browse_key = SecondaryButton("Procurar")
        btn_browse_key.clicked.connect(self._browse_key)
        key_row.addWidget(self.sftp_key_entry, 1)
        key_row.addWidget(btn_browse_key)
        grid.addLayout(key_row, 2, 1, 1, 3)

        grid.addWidget(QLabel("Pasta remota:"), 3, 0)
        self.sftp_remote_entry = QLineEdit(self.state.sftp_remote_path)
        self.sftp_remote_entry.setPlaceholderText("ex.: /backups/estacoes")
        grid.addWidget(self.sftp_remote_entry, 3, 1, 1, 3)

        sftp_card.body_layout().addLayout(grid)

        sftp_btn_row = QHBoxLayout()
        self.btn_test_sftp = SecondaryButton("Testar conexão")
        self.btn_test_sftp.clicked.connect(self._test_sftp)
        sftp_btn_row.addWidget(self.btn_test_sftp)
        sftp_btn_row.addStretch(1)
        sftp_card.body_layout().addLayout(sftp_btn_row)

        self.lbl_sftp_status = QLabel("")
        self.lbl_sftp_status.setObjectName("Muted")
        self.lbl_sftp_status.setWordWrap(True)
        sftp_card.body_layout().addWidget(self.lbl_sftp_status)

        root.addWidget(sftp_card)
        root.addStretch(1)

        self._sftp_test_worker: SftpTestWorker | None = None
        self._on_sftp_toggled(self.chk_sftp_enabled.isChecked())

        # Mantém o AppState sincronizado a cada alteração, mesmo sem clicar
        # em "Testar conexão" (o backup lê state.sftp_* diretamente).
        self.sftp_host_entry.textChanged.connect(lambda _t: self._sync_sftp_state())
        self.sftp_port_spin.valueChanged.connect(lambda _v: self._sync_sftp_state())
        self.sftp_user_entry.textChanged.connect(lambda _t: self._sync_sftp_state())
        self.sftp_password_entry.textChanged.connect(lambda _t: self._sync_sftp_state())
        self.sftp_key_entry.textChanged.connect(lambda _t: self._sync_sftp_state())
        self.sftp_remote_entry.textChanged.connect(lambda _t: self._sync_sftp_state())

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
            icon_lbl.setPixmap(icon_drive(size=20).pixmap(20, 20))
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

    # ── SFTP ──
    def _on_sftp_toggled(self, checked: bool):
        self.state.sftp_enabled = checked
        for widget in (
            self.sftp_host_entry, self.sftp_port_spin, self.sftp_user_entry,
            self.sftp_password_entry, self.sftp_key_entry, self.sftp_remote_entry,
            self.btn_test_sftp,
        ):
            widget.setEnabled(checked)

    def _browse_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar chave privada")
        if path:
            self.sftp_key_entry.setText(path)

    def _sync_sftp_state(self):
        self.state.sftp_enabled = self.chk_sftp_enabled.isChecked()
        self.state.sftp_host = self.sftp_host_entry.text().strip()
        self.state.sftp_port = self.sftp_port_spin.value()
        self.state.sftp_username = self.sftp_user_entry.text().strip()
        self.state.sftp_password = self.sftp_password_entry.text()
        self.state.sftp_private_key_path = self.sftp_key_entry.text().strip()
        self.state.sftp_remote_path = self.sftp_remote_entry.text().strip()

    def _test_sftp(self):
        self._sync_sftp_state()
        if not self.state.sftp_host:
            QMessageBox.warning(self, "Dados incompletos", "Informe pelo menos o host do servidor SFTP.")
            return

        self.btn_test_sftp.setEnabled(False)
        self.lbl_sftp_status.setText("Testando conexão...")
        self.lbl_sftp_status.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self._sftp_test_worker = SftpTestWorker(self.state)
        self._sftp_test_worker.finished_ok.connect(self._on_sftp_test_ok)
        self._sftp_test_worker.failed.connect(self._on_sftp_test_failed)
        self._sftp_test_worker.finished.connect(lambda: self.btn_test_sftp.setEnabled(True))
        self._sftp_test_worker.start()

    def _on_sftp_test_ok(self, message: str):
        self.lbl_sftp_status.setText(f"{icon_html('check', color=theme.SUCCESS)} {message}")
        self.lbl_sftp_status.setStyleSheet(f"color: {theme.SUCCESS};")

    def _on_sftp_test_failed(self, message: str):
        self.lbl_sftp_status.setText(f"{icon_html('warning', color=theme.WARNING)} {message}")
        self.lbl_sftp_status.setStyleSheet(f"color: {theme.WARNING};")
