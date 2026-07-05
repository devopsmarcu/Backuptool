"""
styles/icons.py — Ícones da aplicação.

Prioridade:
1. resources/icons/icon.ico
2. resources/images/icone.png
3. Ícone vetorial desenhado via QPainter (fallback)

Assim a aplicação funciona tanto durante o desenvolvimento quanto após
empacotada, sem depender de bibliotecas externas.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath
from PySide6.QtWidgets import QStyle, QWidget

from styles.dark_theme import ACCENT, TEXT_MAIN

# project_root/styles/icons.py -> project_root/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ICON_ICO_PATH = PROJECT_ROOT / "resources" / "icons" / "icon.ico"
LOGO_PNG_PATH = PROJECT_ROOT / "resources" / "images" / "icone.png"


# ----------------------------------------------------------------------
# Ícones padrão do Qt
# ----------------------------------------------------------------------

def std_icon(widget: QWidget, standard_pixmap: QStyle.StandardPixmap) -> QIcon:
    return widget.style().standardIcon(standard_pixmap)


def icon_folder(widget): return std_icon(widget, QStyle.StandardPixmap.SP_DirIcon)
def icon_refresh(widget): return std_icon(widget, QStyle.StandardPixmap.SP_BrowserReload)
def icon_add(widget): return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogNewFolder)
def icon_remove(widget): return std_icon(widget, QStyle.StandardPixmap.SP_TrashIcon)
def icon_play(widget): return std_icon(widget, QStyle.StandardPixmap.SP_MediaPlay)
def icon_stop(widget): return std_icon(widget, QStyle.StandardPixmap.SP_MediaStop)
def icon_drive(widget): return std_icon(widget, QStyle.StandardPixmap.SP_DriveHDIcon)
def icon_back(widget): return std_icon(widget, QStyle.StandardPixmap.SP_ArrowBack)
def icon_forward(widget): return std_icon(widget, QStyle.StandardPixmap.SP_ArrowForward)
def icon_open(widget): return std_icon(widget, QStyle.StandardPixmap.SP_DialogOpenButton)
def icon_warning(widget): return std_icon(widget, QStyle.StandardPixmap.SP_MessageBoxWarning)
def icon_ok(widget): return std_icon(widget, QStyle.StandardPixmap.SP_DialogApplyButton)
def icon_settings(widget): return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogDetailedView)
def icon_logs(widget): return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogContentsView)


# ----------------------------------------------------------------------
# Fallback vetorial
# ----------------------------------------------------------------------

def _fallback_logo(size: int = 120) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    rect = QRectF(1, 1, size - 2, size - 2)

    path = QPainterPath()
    radius = size * 0.28
    path.addRoundedRect(rect, radius, radius)

    painter.fillPath(path, QColor(ACCENT))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(TEXT_MAIN))

    cx = size / 2
    cy = size / 2

    shield = QPainterPath()

    w = size * 0.34
    h = size * 0.40

    shield.moveTo(cx, cy - h / 2)
    shield.lineTo(cx + w / 2, cy - h / 2 + h * 0.18)
    shield.lineTo(cx + w / 2, cy + h * 0.05)

    shield.cubicTo(
        cx + w / 2,
        cy + h * 0.42,
        cx + w * 0.15,
        cy + h * 0.55,
        cx,
        cy + h / 2,
    )

    shield.cubicTo(
        cx - w * 0.15,
        cy + h * 0.55,
        cx - w / 2,
        cy + h * 0.42,
        cx - w / 2,
        cy + h * 0.05,
    )

    shield.lineTo(cx - w / 2, cy - h / 2 + h * 0.18)
    shield.closeSubpath()

    painter.drawPath(shield)
    painter.end()

    return pm


# ----------------------------------------------------------------------
# Logo da aplicação
# ----------------------------------------------------------------------

def app_logo_pixmap(size: int = 64) -> QPixmap:
    """
    Retorna o logo da aplicação.

    Prioridade:
        1) resources/images/icone.png
        2) fallback vetorial
    """

    if LOGO_PNG_PATH.exists():
        pm = QPixmap(str(LOGO_PNG_PATH))
        if not pm.isNull():
            return pm.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    return _fallback_logo(size)


def app_icon() -> QIcon:

    if ICON_ICO_PATH.exists():
        icon = QIcon(str(ICON_ICO_PATH))
        if not icon.isNull():
            return icon

    if LOGO_PNG_PATH.exists():
        icon = QIcon(str(LOGO_PNG_PATH))
        if not icon.isNull():
            return icon

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_fallback_logo(size))

    return icon