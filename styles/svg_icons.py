"""
styles/svg_icons.py — Ícones SVG inline para UI.

Todos os ícones são 24x24, estilo Feather/Lucide, stroke="currentColor".
"""

from __future__ import annotations

import base64
from typing import Tuple

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

from styles.dark_theme import TEXT_MAIN, TEXT_MUTED, TEXT_DIM, ACCENT, SUCCESS, WARNING, ERROR

# ----------------------------------------------------------------------
# Ícones SVG (24x24)
# ----------------------------------------------------------------------

ICONS = {
    "search": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/>
  <path d="m21 21-4.35-4.35"/>
</svg>
""",
    "disc": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <circle cx="12" cy="12" r="3"/>
</svg>
""",
    "user": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
  <circle cx="12" cy="7" r="4"/>
</svg>
""",
    "folder": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
</svg>
""",
    "chart": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="12" y1="20" x2="12" y2="10"/>
  <line x1="18" y1="20" x2="18" y2="4"/>
  <line x1="6" y1="20" x2="6" y2="16"/>
</svg>
""",
    "forbidden": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="8" y1="8" x2="16" y2="16"/>
</svg>
""",
    "check": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"/>
</svg>
""",
    "warning": """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
  <line x1="12" y1="9" x2="12" y2="13"/>
  <line x1="12" y1="17" x2="12.01" y2="17"/>
</svg>
"""
}

# Cache para pixmaps já renderizados: (name, size, color) -> QPixmap
_PIXMAP_CACHE: dict[Tuple[str, int, str], QPixmap] = {}


def icon_pixmap(name: str, size: int = 24, color: str = TEXT_MAIN) -> QPixmap:
    """Renderiza um ícone SVG em um QPixmap, cacheando o resultado."""
    cache_key = (name, size, color)
    if cache_key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[cache_key]

    svg_content = ICONS.get(name, ICONS["search"])
    svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')

    renderer = QSvgRenderer(svg_content.encode("utf-8"))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    _PIXMAP_CACHE[cache_key] = pixmap
    return pixmap


def icon_label(name: str, size: int = 24, color: str = TEXT_MAIN) -> QLabel:
    """Cria um QLabel com o ícone SVG já setado."""
    label = QLabel()
    label.setPixmap(icon_pixmap(name, size, color))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def icon_html(name: str, size: int = 16, color: str = TEXT_MAIN) -> str:
    """Retorna uma tag <img> com o SVG em base64 para uso em rich text."""
    svg_content = ICONS.get(name, ICONS["search"])
    svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
    svg_content = svg_content.replace('width="24"', f'width="{size}"').replace('height="24"', f'height="{size}"')
    b64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" style="vertical-align: middle;"/>'
