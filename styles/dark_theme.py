"""
styles/dark_theme.py — Paleta de cores e stylesheet (QSS) global do BackupTool.

Este módulo NÃO contém lógica de negócio. Apenas define a identidade visual
(cores, tipografia e QSS) usada por toda a aplicação Qt.
"""

from __future__ import annotations

from string import Template

# ─────────────────────────────────────────────
#  Paleta de cores (Enterprise Dark)
# ─────────────────────────────────────────────
BG_APP        = "#1C2330"   # Fundo geral da janela
BG_HEADER     = "#202734"   # Barra superior / rodapé
BG_CARD       = "#252D3D"   # Cards e superfícies elevadas
BG_CARD_ALT   = "#232B3A"   # Linhas alternadas de tabela
BG_INPUT      = "#1A2130"   # Campos de entrada
BG_HOVER      = "#2D3950"   # Hover genérico
BG_PANEL      = "#2A3346"   # Painéis internos (dentro de cards)
BG_ELEVATED   = "#2B2B36"   # Nível de elevação para GroupBox / Panels

BORDER        = "#3A4557"
BORDER_LIGHT  = "#465066"

TEXT_MAIN     = "#FFFFFF"
TEXT_MUTED    = "#B8C0CC"
TEXT_DIM      = "#7C8798"

ACCENT        = "#3B82F6"
ACCENT_HOVER  = "#2563EB"
ACCENT_PRESS  = "#1D4ED8"
ACCENT_SOFT   = "#3B82F633"   # accent com alpha, para fundos suaves

# Acento secundário — usado para diferenciar visualmente o fluxo de
# Restauração do fluxo de Backup (mesma função do azul, contexto diferente).
RESTORE       = "#14B8A6"
RESTORE_HOVER = "#0D9488"

SUCCESS       = "#22C55E"
WARNING       = "#F59E0B"
ERROR         = "#EF4444"
ERROR_HOVER   = "#DC2626"

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

FONT_FAMILY = "Segoe UI, Inter, Ubuntu, Arial, sans-serif"
FONT_MONO_FAMILY = "JetBrains Mono, Consolas, Monospace"


_QSS_TEMPLATE = Template("""
* {
    font-family: $font_family;
    outline: none;
}

QWidget {
    background-color: $bg_app;
    color: $text_main;
    font-size: 13px;
}

QMainWindow {
    background-color: $bg_app;
}

QToolTip {
    background-color: $bg_panel;
    color: $text_main;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    padding: 6px 10px;
}

/* ── Cards / superfícies ───────────────────────────────────── */
QFrame#Card {
    background-color: $bg_card;
    border: 1px solid $border;
    border-radius: $radius_md px;
}

QGroupBox {
    background-color: $bg_elevated;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    margin-top: 1.2em;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 5px;
    color: $accent;
}

QFrame#Panel {
    background-color: $bg_panel;
    border: 1px solid $border;
    border-radius: $radius_sm px;
}

QLabel#CardTitle {
    color: $accent;
    font-size: 14px;
    font-weight: 600;
}

QLabel#SectionTitle {
    color: $text_main;
    font-size: 17px;
    font-weight: 700;
}

QLabel#SectionSubtitle, QLabel#Muted {
    color: $text_muted;
    font-size: 12px;
}

QLabel#Dim {
    color: $text_dim;
}

/* ── Cabeçalho ─────────────────────────────────────────────── */
QFrame#HeaderBar {
    background-color: $bg_header;
    border-bottom: 1px solid $border;
}

QLabel#AppTitle {
    color: $text_main;
    font-size: 19px;
    font-weight: 700;
}

QPushButton#NavTab {
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: $text_muted;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 0px;
}

QPushButton#NavTab:hover {
    color: $text_main;
    background-color: $bg_hover;
    border-radius: $radius_sm px;
}

QPushButton#NavTab:checked {
    color: $text_main;
    border-bottom: 2px solid $accent;
}

QLabel#SessionInfoTitle {
    color: $text_main;
    font-size: 12px;
    font-weight: 700;
}

QLabel#SessionInfoSub {
    color: $text_muted;
    font-size: 11px;
}

/* ── Stepper ───────────────────────────────────────────────── */
QFrame#StepperBar {
    background-color: transparent;
}

/* ── Botões ────────────────────────────────────────────────── */
QPushButton {
    border-radius: $radius_sm px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid transparent;
}

QPushButton#PrimaryButton {
    background-color: $accent;
    color: #FFFFFF;
}
QPushButton#PrimaryButton:hover  { background-color: $accent_hover; }
QPushButton#PrimaryButton:pressed { background-color: $accent_press; }
QPushButton#PrimaryButton:disabled {
    background-color: $bg_panel;
    color: $text_dim;
}

QPushButton#SuccessButton {
    background-color: $success;
    color: #06210F;
}
QPushButton#SuccessButton:hover { background-color: #16A34A; color: #FFFFFF; }
QPushButton#SuccessButton:disabled {
    background-color: $bg_panel;
    color: $text_dim;
}

QPushButton#RestoreButton {
    background-color: $restore;
    color: #FFFFFF;
}
QPushButton#RestoreButton:hover { background-color: $restore_hover; }
QPushButton#RestoreButton:disabled {
    background-color: $bg_panel;
    color: $text_dim;
}

QPushButton#SecondaryButton {
    background-color: $bg_panel;
    color: $text_muted;
    border: 1px solid $border;
}
QPushButton#SecondaryButton:hover {
    background-color: $bg_hover;
    color: $text_main;
    border: 1px solid $border_light;
}
QPushButton#SecondaryButton:disabled {
    color: $text_dim;
}

QPushButton#DangerButton {
    background-color: $error;
    color: #FFFFFF;
}
QPushButton#DangerButton:hover { background-color: $error_hover; }
QPushButton#DangerButton:disabled {
    background-color: $bg_panel;
    color: $text_dim;
}

QPushButton#GhostButton {
    background-color: transparent;
    color: $text_muted;
    border: 1px solid $border;
    padding: 6px 12px;
}
QPushButton#GhostButton:hover {
    color: $text_main;
    border: 1px solid $border_light;
    background-color: $bg_hover;
}

QPushButton#IconOnly {
    background-color: transparent;
    border: none;
    padding: 4px;
}
QPushButton#IconOnly:hover {
    background-color: $bg_hover;
    border-radius: $radius_sm px;
}

/* ── Inputs ────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: $bg_input;
    color: $text_main;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    padding: 7px 10px;
    selection-background-color: $accent;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid $accent;
}
QLineEdit:disabled {
    color: $text_dim;
}
QLineEdit#SearchInput {
    border: none;
    background-color: transparent;
}

QComboBox {
    background-color: $bg_input;
    color: $text_main;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    padding: 6px 10px;
    min-height: 22px;
}
QComboBox:hover { border: 1px solid $border_light; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: $bg_panel;
    color: $text_main;
    border: 1px solid $border;
    selection-background-color: $accent;
    outline: none;
}

QRadioButton, QCheckBox {
    color: $text_main;
    spacing: 8px;
    padding: 3px 0px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $border_light;
    border-radius: 3px;
    background-color: $bg_input;
}
QCheckBox::indicator {
    border-radius: 4px;
}
QRadioButton::indicator { border-radius: 8px; }
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: $accent;
    border: 1px solid $accent;
}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {
    border: 1px solid $accent;
}

/* ── Tabelas / árvores ─────────────────────────────────────── */
QTableView, QTreeView, QListView {
    background-color: $bg_card;
    alternate-background-color: $bg_card_alt;
    color: $text_main;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    gridline-color: $border;
    selection-background-color: $accent_soft;
    selection-color: $text_main;
}
QTableView::item, QTreeView::item, QListView::item {
    padding: 6px;
    border: none;
}
QTableView::item:hover, QTreeView::item:hover, QListView::item:hover {
    background-color: $bg_hover;
}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {
    background-color: $accent_soft;
    color: $text_main;
}
QHeaderView::section {
    background-color: $bg_panel;
    color: $text_muted;
    padding: 8px;
    border: none;
    border-bottom: 1px solid $border;
    border-right: 1px solid $border;
    font-weight: 700;
    font-size: 11px;
}
QHeaderView::section:hover {
    background-color: $bg_hover;
    color: $text_main;
}
QTableCornerButton::section {
    background-color: $bg_panel;
    border: none;
}

/* ── Barras de rolagem ─────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: $border_light;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: $accent; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    background: transparent;
    height: 11px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: $border_light;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: $accent; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

/* ── Barra de progresso ────────────────────────────────────── */
QProgressBar {
    background-color: $bg_input;
    border: 1px solid $border;
    border-radius: $radius_sm px;
    text-align: center;
    color: $text_main;
    font-weight: 600;
    height: 16px;
}
QProgressBar::chunk {
    background-color: $accent;
    border-radius: $radius_sm px;
}
QProgressBar#RestoreProgress::chunk {
    background-color: $restore;
}

/* ── StatusBar ─────────────────────────────────────────────── */
QStatusBar {
    background-color: $bg_header;
    color: $text_muted;
    border-top: 1px solid $border;
}
QStatusBar::item { border: none; }

/* ── Splitters / Docks ─────────────────────────────────────── */
QSplitter::handle {
    background-color: $border;
}
QSplitter::handle:hover {
    background-color: $accent;
}
QDockWidget {
    color: $text_main;
    titlebar-close-icon: none;
}
QDockWidget::title {
    background-color: $bg_panel;
    padding: 6px;
}

/* ── Menus ─────────────────────────────────────────────────── */
QMenuBar {
    background-color: $bg_header;
    color: $text_main;
}
QMenuBar::item:selected {
    background-color: $bg_hover;
}
QMenu {
    background-color: $bg_panel;
    color: $text_main;
    border: 1px solid $border;
}
QMenu::item:selected {
    background-color: $accent;
}

/* ── Badges de status (dinâmico via propriedade) ──────────── */
QLabel#Badge[state="ok"] {
    background-color: $success;
    color: #06210F;
    border-radius: $radius_sm px;
    padding: 2px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#Badge[state="pending"] {
    background-color: $warning;
    color: #2B1B00;
    border-radius: $radius_sm px;
    padding: 2px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#Badge[state="error"] {
    background-color: $error;
    color: #FFFFFF;
    border-radius: $radius_sm px;
    padding: 2px 10px;
    font-weight: 700;
    font-size: 11px;
}

QFrame#Divider {
    background-color: $border;
    max-height: 1px;
    min-height: 1px;
}
""")


def build_stylesheet() -> str:
    """Monta o QSS final substituindo os tokens de cor pela paleta atual."""
    return _QSS_TEMPLATE.substitute(
        font_family=FONT_FAMILY,
        bg_app=BG_APP,
        bg_header=BG_HEADER,
        bg_card=BG_CARD,
        bg_card_alt=BG_CARD_ALT,
        bg_input=BG_INPUT,
        bg_hover=BG_HOVER,
        bg_panel=BG_PANEL,
        bg_elevated=BG_ELEVATED,
        border=BORDER,
        border_light=BORDER_LIGHT,
        text_main=TEXT_MAIN,
        text_muted=TEXT_MUTED,
        text_dim=TEXT_DIM,
        accent=ACCENT,
        accent_hover=ACCENT_HOVER,
        accent_press=ACCENT_PRESS,
        accent_soft=ACCENT_SOFT,
        restore=RESTORE,
        restore_hover=RESTORE_HOVER,
        success=SUCCESS,
        warning=WARNING,
        error=ERROR,
        error_hover=ERROR_HOVER,
        radius_sm=RADIUS_SM,
        radius_md=RADIUS_MD,
    )
