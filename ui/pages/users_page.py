"""
ui/pages/users_page.py — Aba "1 · Usuários".

Porta fiel de `_build_tab_usuarios` / `_refresh_users` / `_update_selected_users`
(CustomTkinter) para Qt, usando QTableView + QAbstractTableModel (com
QSortFilterProxyModel para busca/ordenação) no lugar da lista de linhas
manuais em um CTkScrollableFrame.

A única função de negócio usada aqui é `core.profiles.detect_user_profiles`,
chamada exatamente como antes.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QAbstractItemView, QHeaderView,
    QLabel, QMessageBox, QSizePolicy, QFileDialog, QInputDialog,
)

from core.profiles import detect_user_profiles, UserProfile
from styles import dark_theme as theme
from styles.svg_icons import icon_add, icon_remove, icon_refresh
from ui.state import AppState
from ui.widgets import SectionIntro, SearchBox, SecondaryButton, DangerButton, EmptyState

COLUMNS = ["", "Nome do Usuário", "Caminho do Perfil", "Último Backup", "Status"]


class UserProfilesModel(QAbstractTableModel):
    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profiles: list[UserProfile] = []
        self._checked: dict[str, bool] = {}

    # ── API pública ──
    def set_profiles(self, profiles: list[UserProfile]):
        self.beginResetModel()
        self._profiles = profiles
        # perfis novos entram marcados por padrão (mesmo comportamento do original)
        self._checked = {p.username: self._checked.get(p.username, True) for p in profiles}
        self.endResetModel()

    def select_all(self):
        for p in self._profiles:
            self._checked[p.username] = True
        if self._profiles:
            top = self.index(0, 0)
            bottom = self.index(len(self._profiles) - 1, 0)
            self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.CheckStateRole])
        self.selection_changed.emit()

    def add_profile(self, profile: UserProfile):
        row = len(self._profiles)
        self.beginInsertRows(QModelIndex(), row, row)
        self._profiles.append(profile)
        self._checked[profile.username] = True
        self.endInsertRows()
        self.selection_changed.emit()

    def remove_checked(self):
        keep = [p for p in self._profiles if not self._checked.get(p.username, False)]
        self.beginResetModel()
        self._profiles = keep
        self._checked = {p.username: self._checked.get(p.username, True) for p in keep}
        self.endResetModel()
        self.selection_changed.emit()

    def has_username(self, username: str) -> bool:
        return any(p.username.lower() == username.lower() for p in self._profiles)

    def checked_profiles(self) -> list[UserProfile]:
        return [p for p in self._profiles if self._checked.get(p.username, False)]

    def profile_at(self, row: int) -> UserProfile:
        return self._profiles[row]

    # ── QAbstractTableModel ──
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._profiles)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        profile = self._profiles[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if self._checked.get(profile.username, False) else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1:
                return profile.username
            if col == 2:
                return profile.path
            if col == 3:
                return "---"
            if col == 4:
                return "Pendente"

        if role == Qt.ItemDataRole.ForegroundRole and col == 4:
            return QColor(theme.WARNING)

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            profile = self._profiles[index.row()]
            self._checked[profile.username] = value == Qt.CheckState.Checked.value or value == Qt.CheckState.Checked
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            self.selection_changed.emit()
            return True
        return False


class _UserFilterProxy(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        model: UserProfilesModel = self.sourceModel()
        text = self.filterRegularExpression().pattern().lower()
        if not text:
            return True
        profile = model.profile_at(source_row)
        return text in profile.username.lower() or text in profile.path.lower()


class UsersPage(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        root.addWidget(SectionIntro(
            "Seleção de usuários",
            "Escolha os perfis detectados automaticamente nesta máquina.",
        ))

        top_bar = QHBoxLayout()
        self.search = SearchBox("Filtrar usuários...")
        self.search.textChanged.connect(self._on_filter_changed)
        top_bar.addWidget(self.search, 1)

        btn_add = SecondaryButton("Adicionar Usuário")
        btn_add.setIcon(icon_add())
        btn_add.clicked.connect(self._add_user_manual)
        btn_remove = DangerButton("Remover Selecionados")
        btn_remove.setIcon(icon_remove())
        btn_remove.clicked.connect(self._remove_selected)
        top_bar.addWidget(btn_add)
        top_bar.addWidget(btn_remove)
        root.addLayout(top_bar)

        self.model = UserProfilesModel(self)
        self.model.selection_changed.connect(self._sync_state)
        self.proxy = _UserFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 36)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 100)
        self.table.setMinimumHeight(220)
        self.table.clicked.connect(self._on_row_clicked)
        root.addWidget(self.table, 1)

        self.empty_state = EmptyState("user", "Nenhum usuário encontrado",
                                       "Ajuste o filtro de busca ou atualize a lista de usuários.")
        self.empty_state.setVisible(False)
        root.addWidget(self.empty_state)

        bottom_bar = QHBoxLayout()
        self.btn_select_all = SecondaryButton("Selecionar Todos")
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_refresh = SecondaryButton("Atualizar Usuários")
        self.btn_refresh.setIcon(icon_refresh())
        self.btn_refresh.clicked.connect(self.refresh_users)
        bottom_bar.addWidget(self.btn_select_all)
        bottom_bar.addWidget(self.btn_refresh)
        bottom_bar.addStretch(1)
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("Muted")
        bottom_bar.addWidget(self.lbl_status)
        root.addLayout(bottom_bar)

        self.refresh_users()

    # ── ações ──
    def refresh_users(self):
        profiles = detect_user_profiles()
        self.state.user_profiles = profiles
        self.model.set_profiles(profiles)
        self.table.resizeRowsToContents()
        self._sync_state()
        self._update_empty_state()

    def _update_empty_state(self):
        has_rows = self.proxy.rowCount() > 0
        self.empty_state.setVisible(not has_rows)
        self.table.setVisible(has_rows)
        if not has_rows and not self.model.rowCount():
            self.empty_state.set_message(
                "Nenhum usuário encontrado",
                "Nenhum perfil de usuário foi detectado nesta máquina. "
                "Clique em \"Atualizar Usuários\" ou adicione um manualmente.",
            )
        elif not has_rows:
            self.empty_state.set_message(
                "Nenhum resultado para o filtro",
                "Ajuste o termo de busca ou limpe o filtro para ver todos os usuários.",
            )

    def _on_filter_changed(self, text: str):
        self.proxy.setFilterRegularExpression(text)
        self._update_empty_state()

    def _on_row_clicked(self, proxy_index):
        # Clicar em qualquer parte da linha alterna o checkbox (melhora a UX
        # em telas touch/laptops sem exigir precisão no quadradinho).
        if proxy_index.column() == 0:
            return
        source_index = self.proxy.mapToSource(proxy_index)
        check_index = self.model.index(source_index.row(), 0)
        current = self.model.data(check_index, Qt.ItemDataRole.CheckStateRole)
        new_state = Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked
        self.model.setData(check_index, new_state, Qt.ItemDataRole.CheckStateRole)

    def _select_all(self):
        self.model.select_all()

    def _sync_state(self):
        selected = self.model.checked_profiles()
        self.state.selected_profiles = selected
        self.lbl_status.setText(f"{len(selected)} usuários selecionados")

    def _add_user_manual(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta do perfil do usuário",
        )
        if not folder:
            return

        default_name = os.path.basename(folder.rstrip("/\\")) or folder
        username, ok = QInputDialog.getText(
            self, "Adicionar Usuário",
            "Nome do usuário para este perfil:",
            text=default_name,
        )
        if not ok or not username.strip():
            return
        username = username.strip()

        if self.model.has_username(username):
            QMessageBox.warning(
                self, "Usuário já existe",
                f'Já existe um usuário chamado "{username}" na lista.',
            )
            return

        self.model.add_profile(UserProfile(username=username, path=folder))
        self.state.user_profiles = list(self.state.user_profiles) + [UserProfile(username=username, path=folder)]
        self.table.resizeRowsToContents()
        self._sync_state()
        self._update_empty_state()

    def _remove_selected(self):
        checked = self.model.checked_profiles()
        if not checked:
            QMessageBox.information(
                self, "Nenhum usuário marcado",
                "Marque o checkbox dos usuários que deseja remover da lista.",
            )
            return
        names = ", ".join(p.username for p in checked)
        confirm = QMessageBox.question(
            self, "Remover Usuários",
            f"Remover {len(checked)} usuário(s) da lista de backup?\n\n{names}\n\n"
            "Isso apenas remove da lista desta execução — não apaga nada em disco.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.model.remove_checked()
        self.state.user_profiles = [p for p in self.state.user_profiles if p.username not in {c.username for c in checked}]
        self._sync_state()
        self._update_empty_state()
