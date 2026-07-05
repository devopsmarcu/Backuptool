"""
ui/widgets.py — Componentes visuais reutilizáveis (design system).

Equivalente aos antigos `create_card`, `create_primary_button`,
`create_status_badge`, `create_empty_state`, etc. do CustomTkinter,
agora como pequenas classes Qt reutilizáveis por todas as páginas.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QSizePolicy,
)

from styles.icons import icon_add
from styles import dark_theme as theme


class Card(QFrame):
    """Container com cantos arredondados, usado para agrupar seções."""

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._body_layout = QVBoxLayout(self)
        self._body_layout.setContentsMargins(16, 14, 16, 16)
        self._body_layout.setSpacing(10)

        if title:
            header = QLabel(title)
            header.setObjectName("CardTitle")
            self._body_layout.addWidget(header)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout


class SectionIntro(QWidget):
    """Título + subtítulo padronizados no topo de cada página."""

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("SectionTitle")
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setObjectName("SectionSubtitle")
        subtitle_lbl.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addWidget(subtitle_lbl)


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class SuccessButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SuccessButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class RestoreActionButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("RestoreButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class SecondaryButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class DangerButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("DangerButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)


class GhostButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("GhostButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class StatusBadge(QLabel):
    """Badge colorido (OK / Pending / Error), estilizado via propriedade QSS."""

    STATE_TEXT = {"ok": "OK", "pending": "Pendente", "error": "Erro"}

    def __init__(self, state: str = "pending", text: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_state(state, text)

    def set_state(self, state: str, text: str | None = None):
        self.setText(text or self.STATE_TEXT.get(state, state))
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class SearchBox(QFrame):
    """Campo de busca com ícone de lupa embutido, usado na aba de Usuários."""

    textChanged = Signal(str)

    def __init__(self, placeholder: str = "Buscar...", parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        lens = QLabel("🔍")
        self.input = QLineEdit()
        self.input.setObjectName("SearchInput")
        self.input.setPlaceholderText(placeholder)
        self.input.textChanged.connect(self.textChanged)

        layout.addWidget(lens)
        layout.addWidget(self.input)

    def text(self) -> str:
        return self.input.text()

    def clear(self):
        self.input.clear()


class EmptyState(QWidget):
    """Estado vazio elegante (ícone + título + descrição), usado quando uma
    lista/tabela ainda não tem dados para mostrar."""

    def __init__(self, icon: str, title: str, description: str, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px;")

        title_lbl = QLabel(title)
        title_lbl.setObjectName("SectionTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_lbl = QLabel(description)
        desc_lbl.setObjectName("Muted")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setMaximumWidth(420)

        outer.addWidget(icon_lbl)
        outer.addSpacing(8)
        outer.addWidget(title_lbl)
        outer.addWidget(desc_lbl)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class MetricTile(QFrame):
    """Pequeno bloco 'Usuário atual / Arquivo atual / Tempo', usado nas
    telas de execução (Backup e Restaurar)."""

    def __init__(self, label: str, value: str = "Aguardando início", parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self._label = QLabel(label)
        self._label.setObjectName("Muted")
        self._value = QLabel(value)
        self._value.setWordWrap(True)
        self._value.setStyleSheet(f"color: {theme.TEXT_MAIN}; font-weight: 600;")

        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, value: str):
        self._value.setText(value)
