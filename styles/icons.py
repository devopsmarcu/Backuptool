"""
styles/icons.py — Ícones da aplicação.

Não depende de nenhum pacote de ícones externo (ex.: qtawesome) nem de
arquivos em resources/icons — assim o projeto continua funcionando em
qualquer máquina só com PySide6 instalado. Usa:
  * QStyle.StandardPixmap para ações comuns (abrir pasta, atualizar, etc.)
  * um pequeno QPainter para desenhar o logotipo (escudo azul arredondado)

Se, no futuro, o projeto passar a ter ícones .svg/.png próprios em
resources/icons/, basta trocar a implementação de `app_logo_pixmap`
para carregar o arquivo — o restante da aplicação não precisa mudar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QStyle, QWidget

from styles.dark_theme import ACCENT, ACCENT_HOVER, TEXT_MAIN


def std_icon(widget: QWidget, standard_pixmap: QStyle.StandardPixmap) -> QIcon:
    """Retorna um ícone padrão do tema Qt atual (mantém consistência com o SO)."""
    return widget.style().standardIcon(standard_pixmap)


# Atalhos semânticos para os ícones mais usados no app -----------------------

def icon_folder(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_DirIcon)


def icon_refresh(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_BrowserReload)


def icon_add(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogNewFolder)


def icon_remove(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_TrashIcon)


def icon_play(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_MediaPlay)


def icon_stop(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_MediaStop)


def icon_drive(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_DriveHDIcon)


def icon_back(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_ArrowBack)


def icon_forward(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_ArrowForward)


def icon_open(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_DialogOpenButton)


def icon_warning(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_MessageBoxWarning)


def icon_ok(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_DialogApplyButton)


def icon_settings(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogDetailedView)


def icon_logs(widget: QWidget) -> QIcon:
    return std_icon(widget, QStyle.StandardPixmap.SP_FileDialogContentsView)


def app_logo_pixmap(size: int = 36) -> QPixmap:
    """Desenha o logotipo do BackupTool: um "escudo" azul arredondado com um
    glifo de disco/seta ao centro. Vetorial (QPainter), sem dependências.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    rect = QRectF(1, 1, size - 2, size - 2)
    path = QPainterPath()
    radius = size * 0.28
    path.addRoundedRect(rect, radius, radius)

    painter.fillPath(path, QColor(ACCENT))

    # Glifo central: um pequeno "escudo" estilizado feito só com formas.
    glyph_color = QColor(TEXT_MAIN)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glyph_color)

    cx, cy = size / 2, size / 2
    shield = QPainterPath()
    w, h = size * 0.34, size * 0.40
    shield.moveTo(cx, cy - h / 2)
    shield.lineTo(cx + w / 2, cy - h / 2 + h * 0.18)
    shield.lineTo(cx + w / 2, cy + h * 0.05)
    shield.cubicTo(cx + w / 2, cy + h * 0.42, cx + w * 0.15, cy + h * 0.55, cx, cy + h / 2)
    shield.cubicTo(cx - w * 0.15, cy + h * 0.55, cx - w / 2, cy + h * 0.42, cx - w / 2, cy + h * 0.05)
    shield.lineTo(cx - w / 2, cy - h / 2 + h * 0.18)
    shield.closeSubpath()
    painter.drawPath(shield)

    painter.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for sz in (16, 24, 32, 48, 64):
        icon.addPixmap(app_logo_pixmap(sz))
    return icon
