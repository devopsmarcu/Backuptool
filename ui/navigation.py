"""
ui/navigation.py — Stepper horizontal (indicador de etapas do assistente).

Equivalente visual ao `_build_stepper` / `_update_stepper` da versão
CustomTkinter, porém como um widget Qt independente e reutilizável,
com sinal de clique para permitir voltar a uma etapa já visitada.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QSizePolicy

from styles import dark_theme as theme


class _StepItem(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, label: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.dot = QToolButton()
        self.dot.setText(str(index + 1))
        self.dot.setFixedSize(26, 26)
        self.dot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dot.clicked.connect(lambda: self.clicked.emit(self.index))

        self.label = QLabel(label)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        layout.addStretch(1)

        self.set_state("upcoming")

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def set_state(self, state: str):
        """state: 'current' | 'done' | 'upcoming'"""
        if state == "current":
            dot_bg, dot_fg, label_color, border = theme.ACCENT, "#FFFFFF", theme.TEXT_MAIN, theme.ACCENT
        elif state == "done":
            dot_bg, dot_fg, label_color, border = theme.BG_PANEL, theme.TEXT_MAIN, theme.TEXT_MUTED, theme.SUCCESS
        else:
            dot_bg, dot_fg, label_color, border = theme.BG_CARD, theme.TEXT_DIM, theme.TEXT_DIM, theme.BORDER

        self.dot.setStyleSheet(
            f"QToolButton {{ background-color: {dot_bg}; color: {dot_fg}; "
            f"border-radius: 13px; border: 1.5px solid {border}; font-weight: 700; font-size: 11px; }}"
        )
        self.label.setStyleSheet(f"color: {label_color}; font-size: 12px; font-weight: 600;")


class Stepper(QFrame):
    """Barra de etapas horizontal. Emite `step_requested(index)` quando o
    usuário clica em uma etapa já concluída (navegação livre para trás)."""

    step_requested = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("StepperBar")
        self._labels = labels
        self._current = 0
        self._max_reached = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        row.setSpacing(18)
        outer.addLayout(row)

        self._items: list[_StepItem] = []
        for i, label in enumerate(labels):
            item = _StepItem(i, label)
            item.clicked.connect(self._on_item_clicked)
            row.addWidget(item)
            self._items.append(item)
        row.addStretch(1)

        self._refresh()

    def _on_item_clicked(self, index: int):
        if index <= self._max_reached:
            self.step_requested.emit(index)

    def set_current_index(self, index: int):
        self._current = index
        self._max_reached = max(self._max_reached, index)
        self._refresh()

    def current_index(self) -> int:
        return self._current

    def _refresh(self):
        for i, item in enumerate(self._items):
            if i == self._current:
                item.set_state("current")
            elif i < self._current:
                item.set_state("done")
            else:
                item.set_state("upcoming")
