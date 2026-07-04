"""
main.py — BackupTool GUI (CustomTkinter)

Abas:
  1 · Usuários    — seleção de perfis para o backup
  2 · Origens      — paths e exclusões
  3 · Destino     — HD externo / pasta de rede
  4 · Resumo      — scan pré-backup
  5 · Backup   — execução do backup
  6 · Restaurar   — restauração a partir de manifest.json
"""

import os
import platform
import shutil
import socket
import subprocess
import threading
import tkinter as tk
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config.defaults import get_default_paths, DEFAULT_EXCLUSIONS, DEFAULT_EXCLUDED_EXTENSIONS
from core.scanner import scan_paths, scan_profile_path, human_size, total_size
from core.backup import run_backup, run_multi_user_backup
from core.destinations import detect_external_drives, validate_destination
from core.report import (
    generate_report,
    generate_multi_user_backup_report,
    generate_multi_user_restore_report,
)
from core.manifest import load_manifest, Manifest
from core.restore import (
    run_restore, generate_restore_report,
    get_manifest_roots, RestoreResult,
    discover_corporate_restore_plans,
    validate_corporate_restore_plan,
    run_corporate_restore,
)
from core.profiles import detect_user_profiles, UserProfile

# ─────────────────────────────────────────────
#  Global Settings & DPI
# ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

if platform.system() == "Windows":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ─────────────────────────────────────────────
#  Design System (Enterprise Dark)
# ─────────────────────────────────────────────
# Colors
ACCENT       = "#3B82F6"  # Corporate Blue
ACCENT_HOVER = "#2563EB"
BG_DARK      = "#0F172A"  # Deep navy-gray
BG_CARD      = "#1E293B"  # Slate blue-gray
BG_PANEL    = "#334155"  # Slightly lighter slate
BG_INPUT     = "#1E293B"  # Match card or slightly darker
TEXT_MAIN    = "#F8FAFC"  # Off-white
TEXT_MUTED   = "#94A3B8"  # Slate gray
SUCCESS      = "#10B981"  # Emerald
WARNING      = "#F59E0B"  # Amber
ERROR_CLR    = "#EF4444"  # Red
RESTORE_CL   = "#0D9488"  # Teal

# Spacing & Geometry
S_XS = 8
S_S  = 12
S_M  = 16
S_L  = 24
S_XL = 32

R_STD = 8    # Standard Border Radius
R_CRD = 10   # Card Border Radius

H_WGT = 40   # Widget Height (Buttons, Inputs)
SZ_ICN = 20  # Icon Size

# Sistema de Fontes Responsivas
def get_font_scale():
    """Calcula o fator de escala com base na resolução da tela e DPI"""
    try:
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        dpi = root.winfo_fpixels('1i')
        root.destroy()
        
        # Base: 1920x1080, 96 DPI → escala 1.0
        base_dpi = 96
        base_width = 1920
        
        dpi_scale = dpi / base_dpi
        width_scale = screen_width / base_width
        
        # Limita a escala entre 0.8 e 1.5 para evitar extremos
        scale = min(max((dpi_scale + width_scale) / 2, 0.8), 1.5)
        return scale
    except Exception:
        return 1.0

FONT_SCALE = get_font_scale()

# Aplicar escalonamento global no CustomTkinter
ctk.set_widget_scaling(FONT_SCALE)
ctk.set_window_scaling(FONT_SCALE)

def get_font(size, weight="normal"):
    """Retorna uma fonte com tamanho escalado"""
    scaled_size = max(8, int(round(size * FONT_SCALE)))
    font_family = "Inter"
    return (font_family, scaled_size, weight)

def get_title_font():
    return get_font(22, "bold")

def get_section_font():
    return get_font(15, "bold")

def get_label_font():
    return get_font(13)

def get_small_font():
    return get_font(12)

def get_mono_font():
    scaled_size = max(8, int(round(10 * FONT_SCALE)))
    font_family = "JetBrains Mono" if platform.system() != "Darwin" else "Menlo"
    return (font_family, scaled_size)

FONT_TITLE = get_title_font()
FONT_SECTION = get_section_font()
FONT_LABEL = get_label_font()
FONT_SMALL = get_small_font()
FONT_MONO = get_mono_font()

TABS = ["1 · Usuários", "2 · Origens", "3 · Destino", "4 · Resumo", "5 · Backup", "6 · Restaurar"]
APP_VERSION = "1.0"
TAB_DESCRIPTIONS = {
    "1 · Usuários": "Escolha quais perfis entram no backup.",
    "2 · Origens": "Revise pastas padrão, pastas extras e exclusões.",
    "3 · Destino": "Selecione onde o backup será salvo.",
    "4 · Resumo": "Confira usuários, arquivos, tamanho e destino antes de iniciar.",
    "5 · Backup": "Acompanhe a execução em tempo real.",
    "6 · Restaurar": "Valide um backup e restaure usuários para o destino corporativo.",
}


# ─────────────────────────────────────────────
#  App principal
# ─────────────────────────────────────────────
class BackupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BackupTool")
        self._configure_window()
        self.configure(fg_color=BG_DARK)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Estado backup ──
        self.paths       = get_default_paths()
        self.exclusions  = list(DEFAULT_EXCLUSIONS)
        self.excl_exts   = list(DEFAULT_EXCLUDED_EXTENSIONS)
        self.destination = ""
        self.scanned     = []
        self.scanned_by_user = {}
        self.last_backup_dir = ""
        self.last_report_path = ""
        self.last_restore_report_path = ""
        self._backup_started_at = 0.0
        self._restore_started_at = 0.0
        self.user_profiles: list[UserProfile] = []
        self.selected_profiles: list[UserProfile] = []
        self._user_vars: dict[str, ctk.BooleanVar] = {}
        self._stop_flag  = False
        self.technician  = socket.gethostname()

        # ── Estado restore ──
        self._restore_manifest: Manifest | None = None
        self._corporate_restore_plans = []
        self._restore_stop      = False
        self._restore_selection: list[str] = []

        self._build_header()
        self._build_stepper()
        self._build_body()
        self._build_footer()
        self._build_status_bar()
        self._on_tab_change()

    # ══════════════════════════════════════════
    #  Layout base
    # ══════════════════════════════════════════

    def _configure_window(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Target mappings
        if screen_w >= 3840:
            target_w, target_h = 1800, 1000
        elif screen_w >= 1920:
            target_w, target_h = 1600, 900
        elif screen_w >= 1366:
            target_w, target_h = 1200, 700
        else:
            target_w, target_h = 1000, 600

        margin_w = 80 if screen_w >= 1600 else 40
        margin_h = 80 if screen_h >= 900 else 48

        width = min(target_w, max(900, screen_w - margin_w))
        height = min(target_h, max(620, screen_h - margin_h))

        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(900, screen_w), min(620, screen_h))
        self.resizable(True, True)

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)

        # Logo & App Name
        logo_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="w", padx=S_M, pady=0)

        ctk.CTkLabel(logo_frame, text="💾", font=get_font(24)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(logo_frame, text="BackupTool",
                     font=FONT_TITLE, text_color=TEXT_MAIN
                     ).pack(side="left")

    def _build_stepper(self):
        self.stepper_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stepper_frame.grid(row=1, column=0, sticky="ew", padx=S_M, pady=(S_S, S_S))
        self.stepper_frame.grid_columnconfigure((0,1,2,3,4,5), weight=1)

        self.step_indicators = []
        step_labels = ["Usuários", "Origem", "Destino", "Resumo", "Backup", "Restaurar"]

        for i, label in enumerate(step_labels):
            container = ctk.CTkFrame(self.stepper_frame, fg_color="transparent")
            container.grid(row=0, column=i, sticky="ew")

            # Circle indicator
            dot = ctk.CTkLabel(container, text=str(i+1),
                               font=get_font(11, "bold"),
                               text_color=TEXT_MUTED,
                               fg_color=BG_CARD,
                               width=24, height=24,
                               corner_radius=12)
            dot.pack(side="left", padx=(S_S, 8))

            lbl = ctk.CTkLabel(container, text=label,
                               font=FONT_SMALL, text_color=TEXT_MUTED)
            lbl.pack(side="left")

            self.step_indicators.append({"dot": dot, "lbl": lbl})

    def _update_stepper(self):
        current_idx = self._current_tab_index()
        for i, item in enumerate(self.step_indicators):
            if i == current_idx:
                item["dot"].configure(fg_color=ACCENT, text_color="white")
                item["lbl"].configure(text_color=TEXT_MAIN)
            elif i < current_idx:
                item["dot"].configure(fg_color=BG_PANEL, text_color=TEXT_MUTED)
                item["lbl"].configure(text_color=TEXT_MUTED)
            else:
                item["dot"].configure(fg_color=BG_CARD, text_color=TEXT_MUTED)
                item["lbl"].configure(text_color=TEXT_MUTED)

    def _build_body(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=BG_CARD,
            segmented_button_fg_color=BG_INPUT,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            text_color=TEXT_MAIN,
            corner_radius=12,
            command=self._on_tab_change,
        )
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=16, pady=(12, 4))
        self.tabview.grid_columnconfigure(0, weight=1)
        self.tabview.grid_rowconfigure(0, weight=1)
        for t in TABS:
            tab = self.tabview.add(t)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._build_tab_usuarios()
        self._build_tab_origem()
        self._build_tab_destino()
        self._build_tab_resumo()
        self._build_tab_progresso()
        self._build_tab_restaurar()

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=56)
        foot.grid(row=3, column=0, sticky="ew")
        foot.grid_columnconfigure(0, weight=0)
        foot.grid_columnconfigure(1, weight=0)
        foot.grid_columnconfigure(2, weight=1)
        foot.grid_columnconfigure(3, weight=0)
        foot.grid_propagate(False)
        self.btn_back = ctk.CTkButton(
            foot, text="← Voltar",
            fg_color=BG_INPUT, hover_color=BG_INPUT,
            text_color=TEXT_MUTED, command=self._go_back)
        self.btn_back.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        self.btn_restart = ctk.CTkButton(
            foot, text="Reiniciar Processo",
            fg_color=BG_INPUT, hover_color=BG_PANEL,
            text_color=TEXT_MUTED, command=self._restart_process)
        self.btn_restart.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=10)
        self.btn_next = ctk.CTkButton(
            foot, text="Próximo →",
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white", command=self._go_next)
        self.btn_next.grid(row=0, column=3, sticky="e", padx=16, pady=10)

    def _build_status_bar(self):
        status = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0, height=28)
        status.grid(row=4, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)
        status.grid_columnconfigure(1, weight=0)
        status.grid_propagate(False)
        self.lbl_status_bar = ctk.CTkLabel(
            status,
            text="Status: pronto",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.lbl_status_bar.grid(row=0, column=0, sticky="ew", padx=16)
        ctk.CTkLabel(
            status,
            text=f"BackupTool {APP_VERSION} · {platform.system()}",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=16)

    # ══════════════════════════════════════════
    #  Reusable UI Components (Design System)
    # ══════════════════════════════════════════

    def create_card(self, parent, title=None):
        """Cria um card com estilo corporativo."""
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=R_CRD)
        if title:
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=S_S, pady=(S_S, S_S))
            ctk.CTkLabel(header, text=title, font=get_font(14, "bold"), text_color=ACCENT).pack(side="left")
        return card

    def create_section_header(self, parent, text):
        """Cria um título de seção padronizado."""
        lbl = ctk.CTkLabel(parent, text=text, font=FONT_SECTION, text_color=TEXT_MAIN)
        # Assumes grid layout in tab
        lbl.grid(row=0, column=0, sticky="ew", padx=S_S, pady=(S_S, S_S))
        return lbl

    def create_primary_button(self, parent, text, command, **kwargs):
        """Botão de ação primária (Azul)."""
        return ctk.CTkButton(
            parent, text=text, command=command,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white", height=H_WGT,
            **kwargs
        )

    def create_secondary_button(self, parent, text, command, **kwargs):
        """Botão de ação secundária (Neutro)."""
        return ctk.CTkButton(
            parent, text=text, command=command,
            fg_color=BG_INPUT, hover_color=BG_PANEL,
            text_color=TEXT_MUTED, height=H_WGT,
            **kwargs
        )

    def create_status_badge(self, parent, text, status_type="OK"):
        """Cria um badge de status colorido."""
        colors = {"OK": SUCCESS, "Pending": WARNING, "Error": ERROR_CLR}
        color = colors.get(status_type, BG_INPUT)
        badge = ctk.CTkFrame(parent, fg_color=color, corner_radius=4, width=60, height=20)
        lbl = ctk.CTkLabel(badge, text=text, font=get_font(10, "bold"), text_color="white")
        lbl.pack(expand=True)
        return badge

    def create_empty_state(self, parent, icon, title, description, cta_text=None, cta_command=None):
        """Estado vazio elegante."""
        frame = ctk.CTkFrame(parent, fg_color=BG_INPUT, corner_radius=R_STD)
        frame.grid(row=0, column=0, sticky="nsew", padx=S_S, pady=S_S)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(expand=True)
        ctk.CTkLabel(content, text=icon, font=get_font(48)).pack(pady=(S_M, S_S))
        ctk.CTkLabel(content, text=title, font=get_section_font(), text_color=TEXT_MAIN).pack(pady=(0, S_S))
        ctk.CTkLabel(content, text=description, font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=500).pack(pady=(0, S_L))
        if cta_text and cta_command:
            self.create_primary_button(content, text=cta_text, command=cta_command).pack()
        return frame

    def create_table_header(self, parent, columns):
        """Cria o cabeçalho de uma tabela enterprise."""
        header = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=0)
        header.pack(fill="x")
        for i, col in enumerate(columns):
            lbl = ctk.CTkLabel(header, text=col, font=get_font(12, "bold"),
                              text_color=TEXT_MUTED, width=150)
            lbl.pack(side="left", padx=S_S, pady=S_S)
        return header

    def create_footer(self, parent):
        """Container padronizado para o rodapé."""
        foot = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, height=H_WGT + S_L)
        foot.grid(row=3, column=0, sticky="ew")
        foot.grid_columnconfigure(2, weight=1)
        foot.grid_propagate(False)
        return foot

    def _screen_intro(self, parent, title, description, accent=ACCENT):
        title_color = accent if accent != ACCENT else TEXT_MAIN
        ctk.CTkLabel(parent, text=title, font=FONT_SECTION,
                     text_color=title_color).grid(row=0, column=0, sticky="ew", padx=S_S, pady=(S_S, S_S))
        ctk.CTkLabel(parent, text=description, font=FONT_SMALL,
                     text_color=TEXT_MUTED, wraplength=900, justify="left"
                     ).grid(row=1, column=0, sticky="ew", padx=S_S, pady=(0, S_S))

    def _on_tab_change(self):
        current = self.tabview.get()
        index = self._current_tab_index() + 1
        self._update_stepper()
        if hasattr(self, "btn_back"):
            self.btn_back.configure(state="normal" if index > 1 else "disabled")
        if hasattr(self, "btn_next"):
            self.btn_next.configure(state="normal" if index < len(TABS) else "disabled")
        if hasattr(self, "lbl_status_bar"):
            self.lbl_status_bar.configure(text=f"Status: {TAB_DESCRIPTIONS.get(current, 'pronto')}")

    def _on_window_resize(self, event):
        # Only trigger if the event is for the main window and not a child
        if event.widget != self:
            return

        width = event.width
        if not hasattr(self, "resumo_cards"):
            return

        if width < 1200:
            # Stack vertically (1 column)
            self.resumo_container.grid_columnconfigure((0,1,2,3), weight=0)
            self.resumo_container.grid_columnconfigure(0, weight=1)
            self.resumo_cards['dest'].grid(row=0, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['stats'].grid(row=1, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['users'].grid(row=2, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['excl'].grid(row=3, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        elif width < 2500:
            # Two columns (normal wide)
            self.resumo_container.grid_columnconfigure((0,1,2,3), weight=0)
            self.resumo_container.grid_columnconfigure((0,1), weight=1)
            self.resumo_cards['dest'].grid(row=0, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['stats'].grid(row=0, column=1, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['users'].grid(row=1, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['excl'].grid(row=1, column=1, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        else:
            # Four columns (ultrawide)
            self.resumo_container.grid_columnconfigure((0,1,2,3), weight=1)
            self.resumo_cards['dest'].grid(row=0, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['stats'].grid(row=0, column=1, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['users'].grid(row=0, column=2, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
            self.resumo_cards['excl'].grid(row=0, column=3, sticky="nsew", padx=S_S // 2, pady=S_S // 2)

    def _format_duration(self, seconds):
        seconds = max(0, int(seconds))
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}h {mins:02d}min"
        if mins:
            return f"{mins}min {secs:02d}s"
        return f"{secs}s"

    def _estimate_remaining(self, started_at, processed, total):
        if not started_at or processed <= 0 or total <= 0:
            return "calculando..."
        elapsed = time.time() - started_at
        remaining = (elapsed / processed) * max(total - processed, 0)
        return self._format_duration(remaining)

    def _short_path(self, path, limit=88):
        if not path:
            return "Aguardando arquivo..."
        return path if len(path) <= limit else "..." + path[-(limit - 3):]

    def _friendly_error(self, message):
        text = str(message)
        if "Permission" in text or "permiss" in text.lower() or "access" in text.lower():
            return "Acesso negado. Verifique permissões no destino selecionado."
        if "No space" in text or "space" in text.lower():
            return "Espaço insuficiente no destino selecionado."
        if "manifest" in text.lower():
            return "Não foi possível validar o backup selecionado."
        return text

    def _validate_backup_ready(self):
        valid, msg = validate_destination(self.destination)
        if not valid:
            messagebox.showerror("Destino não está pronto", self._friendly_error(msg))
            return False
        try:
            free = shutil.disk_usage(self.destination).free
            required = total_size(self.scanned)
            if required > free:
                messagebox.showerror(
                    "Espaço insuficiente",
                    f"O destino possui {human_size(free)} livres, mas o backup precisa de aproximadamente {human_size(required)}."
                )
                return False
        except OSError:
            messagebox.showwarning(
                "Não foi possível conferir o espaço",
                "O destino será usado, mas não foi possível confirmar o espaço livre antes de iniciar."
            )
        return True

    def _open_path(self, path):
        if not path:
            messagebox.showinfo("Nada para abrir", "Nenhum relatório ou pasta disponível ainda.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Não foi possível abrir", self._friendly_error(e))

    def _restart_process(self):
        self._stop_flag = True
        self._restore_stop = True
        self.scanned = []
        self.scanned_by_user = {}
        self.destination = ""
        self.last_backup_dir = ""
        self.last_report_path = ""
        self.last_restore_report_path = ""
        self.progressbar.set(0)
        self.restore_progressbar.set(0)
        self.lbl_status_final.configure(text="")
        self.lbl_restore_status.configure(text="")
        self._log_clear()
        self._restore_log_clear()
        if hasattr(self, "dest_entry"):
            self.dest_entry.delete(0, "end")
        self.tabview.set(TABS[0])
        self._on_tab_change()

    # ══════════════════════════════════════════
    #  Aba 2 — Origens
    # ══════════════════════════════════════════

    def _build_tab_origem(self):
        tab = self.tabview.tab("2 · Origens")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        self._screen_intro(
            tab,
            "Origens do backup",
            "Revise as pastas padrão e adicione locais extras somente quando necessário."
        )

        # --- Paths Card ---
        paths_card = self.create_card(tab, title="Pastas de Origem")
        paths_card.grid(row=2, column=0, sticky="nsew", padx=S_S, pady=S_S)
        paths_card.grid_columnconfigure(0, weight=1)

        self.paths_frame = ctk.CTkScrollableFrame(paths_card, fg_color="transparent", corner_radius=0)
        self.paths_frame.pack(fill="both", expand=True, padx=S_S, pady=S_S)
        self._refresh_paths_list()

        btn_row = ctk.CTkFrame(paths_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=S_S, pady=(0, S_S))
        self.create_primary_button(btn_row, text="➕ Adicionar pasta", command=self._add_path).pack(side="left")

        # --- Exclusions Card ---
        excl_card = self.create_card(tab, title="Exclusões Aplicadas")
        excl_card.grid(row=3, column=0, sticky="nsew", padx=S_S, pady=(0, S_S))
        excl_card.grid_columnconfigure(0, weight=1)

        excl_info = ctk.CTkLabel(excl_card, text="Pastas e extensões ignoradas durante o scan.",
                                 font=FONT_SMALL, text_color=TEXT_MUTED)
        excl_info.pack(anchor="w", padx=S_S, pady=(S_S, S_S))

        self.excl_text = ctk.CTkTextbox(excl_card, font=FONT_MONO,
                                        fg_color=BG_INPUT, text_color=TEXT_MAIN,
                                        border_color=BG_PANEL, border_width=1)
        self.excl_text.pack(fill="both", expand=True, padx=S_S, pady=(0, S_S))
        self.excl_text.insert("end", "\n".join(self.exclusions))

    def _refresh_paths_list(self):
        for w in self.paths_frame.winfo_children():
            w.destroy()
        for p in self.paths:
            row = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
            row.pack(fill="x", pady=S_S // 2)
            ctk.CTkLabel(row, text=p, font=FONT_SMALL,
                         text_color=TEXT_MAIN, anchor="w"
                         ).pack(side="left", fill="x", expand=True, padx=S_S)
            ctk.CTkButton(row, text="✕",
                          fg_color=ERROR_CLR, hover_color="#B91C1C",
                          text_color="white", width=30,
                          command=lambda path=p: self._remove_path(path)
                          ).pack(side="right", padx=(0, S_S))

    def _add_path(self):
        p = filedialog.askdirectory(title="Selecionar pasta")
        if p and p not in self.paths:
            self.paths.append(p)
            self._refresh_paths_list()

    def _remove_path(self, path):
        self.paths.remove(path)
        self._refresh_paths_list()

    # ══════════════════════════════════════════
    #  Aba 1 — Usuários
    # ══════════════════════════════════════════

    def _build_tab_usuarios(self):
        tab = self.tabview.tab("1 · Usuários")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        self._screen_intro(
            tab,
            "Seleção de usuários",
            "Escolha os perfis detectados automaticamente nesta máquina."
        )

        # --- Top Bar (Search & Actions) ---
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=2, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        top_bar.grid_columnconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(top_bar, fg_color=BG_INPUT, corner_radius=S_S, height=H_WGT)
        search_frame.grid(row=0, column=0, sticky="ew", padx=(0, S_S))
        search_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(search_frame, text="🔍", font=get_font(14), text_color=TEXT_MUTED).pack(side="left", padx=(S_S, 0))
        self.user_search_var = ctk.StringVar()
        self.user_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Filtrar usuários...",
            fg_color="transparent",
            text_color=TEXT_MAIN,
            border_width=0,
            textvariable=self.user_search_var,
            command=self._refresh_users # Update list on type
        )
        self.user_search_entry.pack(side="left", fill="x", expand=True, padx=S_S)

        actions_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=1, sticky="e")

        self.create_secondary_button(actions_frame, text="➕ Adicionar", command=self._add_user_manual).pack(side="left", padx=(S_S, 0))
        self.create_secondary_button(actions_frame, text="🗑️ Remover", command=self._remove_selected_user).pack(side="left", padx=S_S)

        # --- Table Area ---
        table_container = ctk.CTkFrame(tab, fg_color=BG_CARD, corner_radius=R_CRD)
        table_container.grid(row=3, column=0, sticky="nsew", padx=S_S, pady=(0, S_S))
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(1, weight=1)

        self.create_table_header(table_container, ["Nome do Usuário", "Caminho do Perfil", "Último Backup", "Status"]).pack(fill="x", padx=S_S, pady=S_S)

        self.users_frame = ctk.CTkScrollableFrame(table_container, fg_color="transparent", corner_radius=0)
        self.users_frame.pack(fill="both", expand=True, padx=S_S, pady=(0, S_S))

        # --- Bottom Actions ---
        bottom_bar = ctk.CTkFrame(tab, fg_color="transparent")
        bottom_bar.grid(row=4, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        bottom_bar.grid_columnconfigure(1, weight=1)

        self.btn_select_all = self.create_secondary_button(bottom_bar, text="Selecionar Todos", command=self._select_all_users)
        self.btn_select_all.grid(row=0, column=0, sticky="w")

        self.btn_refresh_users = self.create_secondary_button(bottom_bar, text="↺ Atualizar Usuários", command=self._refresh_users)
        self.btn_refresh_users.grid(row=0, column=0, sticky="w", padx=(S_S * 2, 0))

        self.lbl_users_status = ctk.CTkLabel(bottom_bar, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_users_status.grid(row=0, column=2, sticky="e")

        self._refresh_users()

    def _refresh_users(self):
        for w in self.users_frame.winfo_children():
            w.destroy()

        self.user_profiles = detect_user_profiles()
        self._user_vars.clear()

        filter_text = self.user_search_var.get().lower()
        filtered_profiles = [p for p in self.user_profiles if filter_text in p.username.lower() or filter_text in p.path.lower()]

        if not filtered_profiles:
            self.create_empty_state(
                self.users_frame,
                "👤",
                "Nenhum usuário encontrado",
                f"Não encontramos perfis correspondentes a '{filter_text}'."
            )
            self.lbl_users_status.configure(text="0 usuários selecionados")
            return

        for i, profile in enumerate(filtered_profiles):
            var = ctk.BooleanVar(value=True)
            self._user_vars[profile.username] = var

            # Table Row
            row = ctk.CTkFrame(self.users_frame, fg_color=BG_PANEL if i % 2 == 0 else "transparent", corner_radius=0)
            row.pack(fill="x", pady=1)

            # Checkbox (Column 0)
            cb = ctk.CTkCheckBox(row, text="", variable=var, width=0,
                                  fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                  command=self._update_selected_users)
            cb.pack(side="left", padx=(S_S, S_S))

            # User Name
            ctk.CTkLabel(row, text=profile.username, font=get_font(13), text_color=TEXT_MAIN, width=150, anchor="w").pack(side="left", padx=S_S)
            # Path
            ctk.CTkLabel(row, text=profile.path, font=FONT_SMALL, text_color=TEXT_MUTED, width=300, anchor="w").pack(side="left", padx=S_S)
            # Last Backup (Mock for UI)
            ctk.CTkLabel(row, text="---", font=FONT_SMALL, text_color=TEXT_MUTED, width=150, anchor="w").pack(side="left", padx=S_S)
            # Status Badge
            self.create_status_badge(row, "Pendente", "Pending").pack(side="left", padx=S_S)

        self._update_selected_users()

    def _add_user_manual(self):
        # Placeholder for manual add functionality as it's a UI request
        messagebox.showinfo("Funcionalidade", "A adição manual de usuários será implementada na versão 2.2.")

    def _remove_selected_user(self):
        # This would remove the current selected user from the list
        # For now, it's a UI placeholder as per a "modernize UI" request
        messagebox.showwarning("Remover Usuário", "Por favor, desmarque o checkbox do usuário para removê-lo do backup.")

    def _select_all_users(self):
        for var in self._user_vars.values():
            var.set(True)
        self._update_selected_users()

    def _update_selected_users(self):
        selected = []
        for profile in self.user_profiles:
            var = self._user_vars.get(profile.username)
            if var and var.get():
                selected.append(profile)
        self.selected_profiles = selected
        self.lbl_users_status.configure(text=f"{len(selected)} usuários selecionados")

    # ══════════════════════════════════════════
    #  Aba 3 — Destino
    # ══════════════════════════════════════════

    def _build_tab_destino(self):
        tab = self.tabview.tab("3 · Destino")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        self._screen_intro(
            tab,
            "Destino do backup",
            "Use um dispositivo detectado ou selecione uma pasta de rede/local com espaço suficiente."
        )

        # --- Detected Drives Card ---
        drives_card = self.create_card(tab, title="Dispositivos Detectados")
        drives_card.grid(row=2, column=0, sticky="nsew", padx=S_S, pady=S_S)
        drives_card.grid_columnconfigure(0, weight=1)

        self.drives_frame = ctk.CTkScrollableFrame(drives_card, fg_color="transparent", corner_radius=0)
        self.drives_frame.pack(fill="both", expand=True, padx=S_S, pady=S_S)

        btn_row = ctk.CTkFrame(drives_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=S_S, pady=(0, S_S))
        self.create_secondary_button(btn_row, text="↺ Atualizar dispositivos", command=self._refresh_drives).pack(side="left")

        self._refresh_drives()

        # --- Manual Selection Card ---
        manual_card = self.create_card(tab, title="Seleção Manual")
        manual_card.grid(row=3, column=0, sticky="nsew", padx=S_S, pady=(0, S_S))
        manual_card.grid_columnconfigure(0, weight=1)

        input_frame = ctk.CTkFrame(manual_card, fg_color="transparent")
        input_frame.pack(fill="x", padx=S_S, pady=S_S)
        input_frame.grid_columnconfigure(0, weight=1)

        self.dest_entry = ctk.CTkEntry(
            input_frame, placeholder_text=r"Ex: \\servidor\backup  ou  /mnt/externo",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_PANEL,
            height=H_WGT
        )
        self.dest_entry.grid(row=0, column=0, sticky="ew")

        self.create_primary_button(input_frame, text="Procurar", command=self._browse_dest).grid(row=0, column=1, padx=(S_S, 0))

        self.lbl_dest_status = ctk.CTkLabel(manual_card, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_dest_status.pack(anchor="w", padx=S_S, pady=(0, S_S))

    def _refresh_drives(self):
        for w in self.drives_frame.winfo_children():
            w.destroy()
        drives = detect_external_drives()
        if not drives:
            self.create_empty_state(
                self.drives_frame,
                "💿",
                "Nenhum dispositivo detectado",
                "Tente conectar um HD externo ou mapear uma unidade de rede."
            )
            return
        for d in drives:
            row = ctk.CTkFrame(self.drives_frame, fg_color="transparent")
            row.pack(fill="x", pady=S_S // 2)
            ctk.CTkLabel(row,
                         text=f"  {d['label']}  [{d['type']}]  —  {d['path']}",
                         font=FONT_SMALL, text_color=TEXT_MAIN, anchor="w"
                         ).pack(side="left", fill="x", expand=True, padx=S_S)
            self.create_primary_button(row, text="Usar", command=lambda path=d["path"]: self._select_drive(path), width=80).pack(side="right", padx=(0, S_S))

    def _select_drive(self, path):
        self.dest_entry.delete(0, "end")
        self.dest_entry.insert(0, path)
        self.lbl_dest_status.configure(text=f"✔ Selecionado: {path}", text_color=SUCCESS)

    def _browse_dest(self):
        p = filedialog.askdirectory(title="Selecionar destino")
        if p:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, p)

    # ══════════════════════════════════════════
    #  Aba 4 — Resumo
    # ══════════════════════════════════════════

    def _build_tab_resumo(self):
        tab = self.tabview.tab("4 · Resumo")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        self._screen_intro(
            tab,
            "Resumo e validação",
            "Confira usuários, arquivos, tamanho estimado, destino e exclusões antes de executar."
        )

        # Container para os cards
        self.resumo_container = ctk.CTkScrollableFrame(tab, fg_color="transparent", corner_radius=0)
        self.resumo_container.grid(row=2, column=0, sticky="nsew", padx=S_S, pady=(S_S, S_S))
        self.resumo_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Cards de informação
        self.resumo_cards = {}

        # Card: Destino
        self.resumo_cards['dest'] = self.create_card(self.resumo_container, title="Destino")
        self.resumo_cards['dest'].grid(row=0, column=0, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        self.lbl_resumo_dest = ctk.CTkLabel(self.resumo_cards['dest'], text="Aguardando scan...",
                                           font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_resumo_dest.pack(fill="x", padx=S_S, pady=(0, S_S))

        # Card: Arquivos e Tamanho
        self.resumo_cards['stats'] = self.create_card(self.resumo_container, title="Estatísticas")
        self.resumo_cards['stats'].grid(row=0, column=1, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        self.lbl_resumo_stats = ctk.CTkLabel(self.resumo_cards['stats'], text="Aguardando scan...",
                                             font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_resumo_stats.pack(fill="x", padx=S_S, pady=(0, S_S))

        # Card: Usuários
        self.resumo_cards['users'] = self.create_card(self.resumo_container, title="Usuários")
        self.resumo_cards['users'].grid(row=0, column=2, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        self.lbl_resumo_users = ctk.CTkLabel(self.resumo_cards['users'], text="Aguardando scan...",
                                             font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_resumo_users.pack(fill="x", padx=S_S, pady=(0, S_S))

        # Card: Exclusões
        self.resumo_cards['excl'] = self.create_card(self.resumo_container, title="Exclusões")
        self.resumo_cards['excl'].grid(row=0, column=3, sticky="nsew", padx=S_S // 2, pady=S_S // 2)
        self.lbl_resumo_excl = ctk.CTkLabel(self.resumo_cards['excl'], text="Aguardando scan...",
                                             font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_resumo_excl.pack(fill="x", padx=S_S, pady=(0, S_S))

        # Action button at the bottom
        self.btn_scan = self.create_primary_button(tab, text="Validar e gerar resumo", command=self._start_scan)
        self.btn_scan.grid(row=3, column=0, pady=S_S)

        # Bind resize event to the window
        self.bind("<Configure>", self._on_window_resize)

    def _start_scan(self):
        self._sync_exclusions()
        self._update_selected_users()
        dest = self.dest_entry.get().strip()
        valid, msg = validate_destination(dest)
        if not valid:
            messagebox.showerror("Destino inválido", msg)
            return
        self.destination = dest
        self.btn_scan.configure(state="disabled", text="Escaneando...")
        self._set_resumo("Preparando resumo. A varredura pode levar alguns minutos em perfis grandes.\n")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        count = [0]
        def on_file(path):
            count[0] += 1
            if count[0] % 50 == 0:
                self.after(0, lambda: self._set_resumo(
                    f"Varredura em andamento\n\nArquivos encontrados: {count[0]}\nA interface continua ativa."))

        self.scanned_by_user = {}
        res_data = {}

        if self.selected_profiles:
            self.scanned = []
            total_b = 0
            user_lines = []
            for profile in self.selected_profiles:
                entries = scan_profile_path(profile.path, self.exclusions, self.excl_exts, on_file)
                self.scanned_by_user[profile.username] = entries
                self.scanned.extend(entries)
                user_total = total_size(entries)
                total_b += user_total
                user_lines.append(f"{profile.username}: {len(entries)} arquivos · {human_size(user_total)}")

            res_data['users'] = "\n".join(user_lines)
            res_data['stats'] = f"Arquivos: {len(self.scanned)}\nTamanho: {human_size(total_b)}"
        else:
            self.scanned = scan_paths(self.paths, self.exclusions, self.excl_exts, on_file)
            total_b = total_size(self.scanned)
            res_data['users'] = "Pastas incluídas:\n" + "\n".join([f"- {p}" for p in self.paths])
            res_data['stats'] = f"Arquivos: {len(self.scanned)}\nTamanho: {human_size(total_b)}"

        res_data['dest'] = f"Destino: {self.destination}"

        try:
            free = shutil.disk_usage(self.destination).free
            res_data['dest'] += f"\nEspaço livre: {human_size(free)}"
        except OSError:
            res_data['dest'] += "\nEspaço livre: não disponível"

        excl_list = [f"- {item}" for item in self.exclusions[:12]]
        if len(self.exclusions) > 12:
            excl_list.append(f"- ... e mais {len(self.exclusions) - 12} exclusões")
        res_data['excl'] = "\n".join(excl_list)

        self.after(0, lambda: self._set_resumo(res_data))
        self.after(0, lambda: self.btn_scan.configure(
            state="normal", text="Atualizar resumo"))

    def _set_resumo(self, data):
        if isinstance(data, str):
            # Status message - put it in the cards or a dedicated area
            # For simplicity, put it in the stats card
            self.lbl_resumo_stats.configure(text=data)
            return

        # Update cards with structured data
        self.lbl_resumo_dest.configure(text=data.get('dest', ''))
        self.lbl_resumo_stats.configure(text=data.get('stats', ''))
        self.lbl_resumo_users.configure(text=data.get('users', ''))
        self.lbl_resumo_excl.configure(text=data.get('excl', ''))

    # ══════════════════════════════════════════
    #  Aba 5 — Backup
    # ══════════════════════════════════════════

    def _build_tab_progresso(self):
        tab = self.tabview.tab("5 · Backup")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(5, weight=1)

        self._screen_intro(
            tab,
            "Execução do backup",
            "Acompanhe usuário atual, arquivo processado, progresso e tempo estimado restante."
        )

        # --- Status Card ---
        status_card = self.create_card(tab, title="Monitoramento de Cópia")
        status_card.grid(row=2, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        status_card.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_backup_user = ctk.CTkLabel(status_card, text="Usuário atual\nAguardando início",
                                            font=FONT_SMALL, text_color=TEXT_MAIN,
                                            justify="left", anchor="w")
        self.lbl_backup_user.grid(row=0, column=0, sticky="ew", padx=S_S, pady=S_S)

        self.lbl_current = ctk.CTkLabel(status_card, text="Arquivo atual\nAguardando início",
                                        font=FONT_SMALL, text_color=TEXT_MAIN,
                                        justify="left", anchor="w")
        self.lbl_current.grid(row=0, column=1, sticky="ew", padx=S_S, pady=S_S)

        self.lbl_backup_time = ctk.CTkLabel(status_card, text="Tempo\n0s · restante calculando...",
                                            font=FONT_SMALL, text_color=TEXT_MAIN,
                                            justify="left", anchor="w")
        self.lbl_backup_time.grid(row=0, column=2, sticky="ew", padx=S_S, pady=S_S)

        # --- Progress Section ---
        progress_frame = ctk.CTkFrame(tab, fg_color="transparent")
        progress_frame.grid(row=3, column=0, sticky="ew", padx=S_S, pady=(S_S, S_S))
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(progress_frame, height=16,
                                               fg_color=BG_INPUT, progress_color=ACCENT)
        self.progressbar.grid(row=0, column=0, sticky="ew")
        self.progressbar.set(0)

        self.lbl_percentage = ctk.CTkLabel(progress_frame, text="0%",
                                           font=get_font(14, "bold"),
                                           text_color=TEXT_MAIN,
                                           width=60)
        self.lbl_percentage.grid(row=0, column=1, padx=(S_S, 0))

        self.lbl_counter = ctk.CTkLabel(tab, text="Progresso: 0 / 0 arquivos",
                                         font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_counter.grid(row=4, column=0, sticky="e", padx=S_S)

        # --- Logs Area ---
        self.log_box = ctk.CTkTextbox(tab, font=FONT_MONO,
                                       fg_color=BG_INPUT, text_color=TEXT_MAIN,
                                       border_color=BG_PANEL, border_width=1,
                                       state="disabled")
        self.log_box.grid(row=5, column=0, sticky="nsew", padx=S_S, pady=(S_S, S_S))

        # --- Action Row ---
        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=6, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        btn_row.grid_columnconfigure(4, weight=1)

        self.btn_start = self.create_primary_button(btn_row, text="Iniciar Backup", command=self._start_backup, fg_color=SUCCESS, hover_color="#16A34A")
        self.btn_start.grid(row=0, column=0, sticky="w")

        self.btn_stop = self.create_secondary_button(btn_row, text="Cancelar Backup", command=self._stop_backup, fg_color=ERROR_CLR, hover_color="#B91C1C", text_color="white", state="disabled")
        self.btn_stop.grid(row=0, column=1, sticky="w", padx=S_S)

        self.create_secondary_button(btn_row, text="Abrir Relatório", command=lambda: self._open_path(self.last_report_path)).grid(row=0, column=2, sticky="w", padx=(S_S, 0))
        self.create_secondary_button(btn_row, text="Abrir Pasta", command=lambda: self._open_path(self.last_backup_dir)).grid(row=0, column=3, sticky="w", padx=S_S)

        self.lbl_status_final = ctk.CTkLabel(btn_row, text="",
                                              font=get_font(12, "bold"),
                                              text_color=TEXT_MUTED)
        self.lbl_status_final.grid(row=0, column=4, sticky="e")

    def _start_backup(self):
        if not self.scanned:
            messagebox.showwarning("Scan necessário",
                                   "Execute o scan na aba Resumo antes de iniciar o backup.")
            return
        if not self._validate_backup_ready():
            return
        self._stop_flag = False
        self._backup_started_at = time.time()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status_final.configure(text="")
        self.lbl_backup_user.configure(text="Usuário atual\nPreparando...")
        self.lbl_current.configure(text="Arquivo atual\nPreparando...")
        self.lbl_backup_time.configure(text="Tempo\n0s · restante calculando...")
        self._log_clear()
        threading.Thread(target=self._backup_thread, daemon=True).start()

    def _stop_backup(self):
        self._stop_flag = True
        self.btn_stop.configure(state="disabled")

    def _backup_thread(self):
        if self.selected_profiles and self.scanned_by_user:
            def on_user_progress(user, i, t, path, copied, total):
                self.after(0, lambda: self._update_user_progress(user, i, t, path, copied, total))

            result = run_multi_user_backup(
                self.scanned_by_user,
                self.selected_profiles,
                self.destination,
                on_progress=on_user_progress,
                stop_flag=lambda: self._stop_flag,
            )
            report_path, csv_path = generate_multi_user_backup_report(
                result,
                self.destination,
                technician=self.technician,
                machine=socket.gethostname(),
            )
            self.after(0, lambda: self._multi_backup_done(result, report_path, csv_path))
            return

        def on_progress(i, t, path):
            self.after(0, lambda: self._update_progress(i, t, path))

        result = run_backup(
            self.scanned, self.destination,
            on_progress=on_progress,
            stop_flag=lambda: self._stop_flag,
        )
        report_path = generate_report(
            self.scanned, result, self.destination,
            technician=self.technician,
            machine=socket.gethostname(),
            output_dir=os.path.join(os.path.dirname(__file__), "logs"),
        )
        self.after(0, lambda: self._backup_done(result, report_path))

    def _update_progress(self, i, total, path):
        self.progressbar.set(i / total if total else 0)
        self.lbl_counter.configure(text=f"Progresso: {i} / {total} arquivos")
        self.lbl_backup_user.configure(text="Usuário atual\nBackup manual")
        self.lbl_current.configure(text=f"Arquivo atual\n{self._short_path(path)}")
        elapsed = self._format_duration(time.time() - self._backup_started_at)
        remaining = self._estimate_remaining(self._backup_started_at, i, total)
        self.lbl_backup_time.configure(text=f"Tempo\n{elapsed} · restante {remaining}")
        self._log_append(f"[{i:>5}/{total}] {os.path.basename(path)}\n")

    def _update_user_progress(self, user, i, total, path, copied, overall_total):
        self.progressbar.set(copied / overall_total if overall_total else 0)
        self.lbl_counter.configure(text=f"Progresso: {copied} / {overall_total} arquivos")
        self.lbl_backup_user.configure(text=f"Usuário atual\n{user}")
        self.lbl_current.configure(text=f"Arquivo atual\n{self._short_path(path)}")
        elapsed = self._format_duration(time.time() - self._backup_started_at)
        remaining = self._estimate_remaining(self._backup_started_at, copied, overall_total)
        self.lbl_backup_time.configure(text=f"Tempo\n{elapsed} · restante {remaining}")
        self._log_append(f"[{copied:>5}/{overall_total}] {user}: {os.path.basename(path)}\n")

    def _backup_done(self, result, report_path):
        self.progressbar.set(1)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.last_backup_dir = result.backup_dir
        self.last_report_path = report_path

        if result.errors == 0:
            color, msg = SUCCESS, f"✔ Concluído — {result.copied} arquivos copiados"
        else:
            color = WARNING
            msg = f"⚠ Concluído com erros — {result.copied} copiados, {result.errors} erros"

        self.lbl_status_final.configure(text=msg, text_color=color)
        self.lbl_backup_time.configure(
            text=f"Tempo\n{self._format_duration(time.time() - self._backup_started_at)} · concluído"
        )
        self._log_append(f"\n{msg}\n")
        if result.manifest_path:
            self._log_append(f"manifest.json: {result.manifest_path}\n")
        self._log_append(f"Relatório:     {report_path}\n")

        if result.errors:
            self._log_append("\n── Erros ──\n")
            for err in result.error_details:
                self._log_append(f"  {err['file']}: {err['error']}\n")

    def _multi_backup_done(self, result, report_path, csv_path):
        self.progressbar.set(1)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.last_backup_dir = result.backup_dir
        self.last_report_path = report_path

        if result.errors == 0:
            color, msg = SUCCESS, f"✔ Concluído — {result.copied} arquivos copiados"
        else:
            color = WARNING
            msg = f"⚠ Concluído com erros — {result.copied} copiados, {result.errors} erros"

        self.lbl_status_final.configure(text=msg, text_color=color)
        self.lbl_backup_time.configure(
            text=f"Tempo\n{self._format_duration(result.elapsed_seconds)} · concluído"
        )
        self._log_append(f"\n{msg}\n")
        self._log_append(f"Backup:        {result.backup_dir}\n")
        self._log_append(f"Relatório JSON: {report_path}\n")
        self._log_append(f"Relatório CSV : {csv_path}\n")

        for user_result in result.user_results:
            self._log_append(
                f"  {user_result.user}: {user_result.copied} copiados, "
                f"{user_result.errors} erros\n"
            )

        if result.errors:
            self._log_append("\n── Erros ──\n")
            for err in result.error_details:
                self._log_append(f"  {err.get('user', '')} {err['file']}: {err['error']}\n")

    def _log_append(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _log_clear(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ══════════════════════════════════════════
    #  Aba 6 — Restaurar
    # ══════════════════════════════════════════

    def _build_tab_restaurar(self):
        tab = self.tabview.tab("6 · Restaurar")
        tab.grid_columnconfigure(0, weight=1)

        self._screen_intro(
            tab,
            "Restauração",
            "Selecione uma pasta de backup, valide os arquivos e acompanhe a restauração com segurança.",
            accent=RESTORE_CL,
        )

        # --- Source Selection Card ---
        src_card = self.create_card(tab, title="Origem do Backup")
        src_card.grid(row=2, column=0, sticky="ew", padx=S_S, pady=S_S)
        src_card.grid_columnconfigure(0, weight=1)

        row_src = ctk.CTkFrame(src_card, fg_color="transparent")
        row_src.pack(fill="x", padx=S_S, pady=S_S)
        row_src.grid_columnconfigure(0, weight=1)

        self.restore_src_entry = ctk.CTkEntry(
            row_src, placeholder_text="Pasta do backup",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_PANEL,
            height=H_WGT
        )
        self.restore_src_entry.grid(row=0, column=0, sticky="ew")

        self.create_primary_button(row_src, text="Procurar", command=self._browse_restore_src, fg_color=RESTORE_CL, hover_color="#0F766E").grid(row=0, column=1, padx=(S_S, 0))

        self.lbl_manifest_info = ctk.CTkLabel(src_card, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_manifest_info.pack(anchor="w", padx=S_S, pady=(0, S_S))

        # --- Validation Card ---
        val_card = self.create_card(tab, title="Validação e Mapeamento")
        val_card.grid(row=3, column=0, sticky="nsew", padx=S_S, pady=(0, S_S))
        val_card.grid_columnconfigure(0, weight=1)

        self.corporate_preview_frame = ctk.CTkScrollableFrame(val_card, fg_color="transparent", corner_radius=0)
        self.corporate_preview_frame.pack(fill="both", expand=True, padx=S_S, pady=S_S)

        # --- Configuration Card ---
        conf_card = self.create_card(tab, title="Configurações de Restauro")
        conf_card.grid(row=4, column=0, sticky="ew", padx=S_S, pady=S_S)

        conf_content = ctk.CTkFrame(conf_card, fg_color="transparent")
        conf_content.pack(fill="both", expand=True, padx=S_S, pady=S_S)
        conf_content.grid_columnconfigure((0, 1), weight=1)

        # Mode Pane
        pane_mode = ctk.CTkFrame(conf_content, fg_color=BG_PANEL, corner_radius=R_STD)
        pane_mode.grid(row=0, column=0, sticky="nsew", padx=S_S, pady=S_S)
        ctk.CTkLabel(pane_mode, text="Modo de restauração", font=get_font(11, "bold"), text_color=TEXT_MAIN).grid(row=0, column=0, sticky="w", padx=S_S, pady=(S_S, S_S))

        self.restore_mode = ctk.StringVar(value="all")
        for i, (val, label) in enumerate([
            ("all",       "Restaurar tudo"),
            ("selection", "Restaurar seleção"),
            ("alternate", "Restaurar para outro local"),
        ]):
            ctk.CTkRadioButton(pane_mode, text=label, variable=self.restore_mode,
                               value=val, text_color=TEXT_MAIN,
                               fg_color=RESTORE_CL, hover_color="#0F766E",
                               command=self._on_restore_mode_change
                               ).grid(row=i+1, column=0, sticky="w", padx=S_S * 2, pady=2)

        # Conflict Pane
        pane_conf = ctk.CTkFrame(conf_content, fg_color=BG_PANEL, corner_radius=R_STD)
        pane_conf.grid(row=0, column=1, sticky="nsew", padx=S_S, pady=S_S)
        ctk.CTkLabel(pane_conf, text="Políticas de Conflito", font=get_font(11, "bold"), text_color=TEXT_MAIN).grid(row=0, column=0, sticky="w", padx=S_S, pady=(S_S, S_S))

        self.conflict_mode = ctk.StringVar(value="overwrite")
        for i, (val, label) in enumerate([
            ("overwrite", "Sobrescrever"),
            ("ask",       "Perguntar"),
            ("ignore",    "Ignorar"),
        ]):
            ctk.CTkRadioButton(pane_conf, text=label, variable=self.conflict_mode,
                               value=val, text_color=TEXT_MAIN,
                               fg_color=RESTORE_CL, hover_color="#0F766E",
                               ).grid(row=i+1, column=0, sticky="w", padx=S_S * 2, pady=2)

        # --- Dynamic Selection Frames (Hidden by default) ---
        # NOTE: these are children of `tab`, which is a grid-managed container.
        # They must therefore use grid() (not pack()) to show/hide themselves,
        # otherwise Tkinter raises "cannot use geometry manager pack inside
        # ... which already has slaves managed by grid".
        self.frame_alt_dest = ctk.CTkFrame(tab, fg_color="transparent")
        self.frame_alt_dest.grid(row=5, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        ctk.CTkLabel(self.frame_alt_dest, text="Pasta de destino alternativa", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(S_S, 2))
        row_alt = ctk.CTkFrame(self.frame_alt_dest, fg_color="transparent")
        row_alt.pack(fill="x")
        self.restore_alt_entry = ctk.CTkEntry(
            row_alt, placeholder_text="Ex: D:\\Recuperacao  ou  /mnt/recuperacao",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_PANEL, height=H_WGT)
        self.restore_alt_entry.pack(side="left", fill="x", expand=True)
        self.create_primary_button(row_alt, text="Procurar", command=self._browse_alt_dest, fg_color=RESTORE_CL, hover_color="#0F766E").pack(side="right", padx=(S_S, 0))
        self.frame_alt_dest.grid_remove()

        self.frame_selection = ctk.CTkFrame(tab, fg_color="transparent")
        self.frame_selection.grid(row=5, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        ctk.CTkLabel(self.frame_selection, text="Selecione quais pastas restaurar", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(S_S, 2))
        self.selection_frame = ctk.CTkScrollableFrame(self.frame_selection, fg_color=BG_INPUT, corner_radius=R_STD)
        self.selection_frame.pack(fill="x")
        self._selection_vars: dict[str, ctk.BooleanVar] = {}
        self.frame_selection.grid_remove()

        # --- Progress & Logs ---
        restore_status = self.create_card(tab, title="Status da Restauração")
        restore_status.grid(row=6, column=0, sticky="ew", padx=S_S, pady=S_S)
        restore_status.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_restore_user = ctk.CTkLabel(restore_status, text="Usuário atual\nAguardando início", font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_restore_user.grid(row=0, column=0, sticky="ew", padx=S_S, pady=S_S)
        self.lbl_restore_current = ctk.CTkLabel(restore_status, text="Arquivo atual\nAguardando início", font=FONT_SMALL, text_color=TEXT_MAIN, anchor="w", justify="left")
        self.lbl_restore_current.grid(row=0, column=1, sticky="ew", padx=S_S, pady=S_S)
        self.lbl_restore_time = ctk.CTkLabel(restore_status, text="Tempo\n0s · restante calculando...", font=FONT_SMALL, text_color=TEXT_MAIN, justify="left", anchor="w")
        self.lbl_restore_time.grid(row=0, column=2, sticky="ew", padx=S_S, pady=S_S)

        self.restore_progressbar = ctk.CTkProgressBar(tab, height=14, fg_color=BG_INPUT, progress_color=RESTORE_CL)
        self.restore_progressbar.grid(row=7, column=0, sticky="ew", padx=S_S, pady=(S_S, S_S))

        self.lbl_restore_counter = ctk.CTkLabel(tab, text="Progresso: 0 / 0 arquivos", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_restore_counter.grid(row=8, column=0, sticky="e", padx=S_S)

        self.restore_log = ctk.CTkTextbox(tab, font=FONT_MONO, fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_PANEL, border_width=1, state="disabled")
        self.restore_log.grid(row=9, column=0, sticky="nsew", padx=S_S, pady=(S_S, S_S))
        tab.grid_rowconfigure(9, weight=1)

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=10, column=0, sticky="ew", padx=S_S, pady=(0, S_S))
        btn_row.grid_columnconfigure(3, weight=1)

        self.btn_restore_start = self.create_primary_button(btn_row, text="Iniciar Restauração", command=self._start_restore, fg_color=RESTORE_CL, hover_color="#0F766E")
        self.btn_restore_start.grid(row=0, column=0, sticky="w")

        self.btn_restore_stop = self.create_secondary_button(btn_row, text="Cancelar Restauração", command=self._stop_restore, fg_color=ERROR_CLR, hover_color="#B91C1C", text_color="white", state="disabled")
        self.btn_restore_stop.grid(row=0, column=1, sticky="w", padx=S_S)

        self.create_secondary_button(btn_row, text="Abrir Relatório", command=lambda: self._open_path(self.last_restore_report_path)).grid(row=0, column=2, sticky="w", padx=(S_S, 0))

        self.lbl_restore_status = ctk.CTkLabel(btn_row, text="", font=get_font(12, "bold"), text_color=TEXT_MUTED)
        self.lbl_restore_status.grid(row=0, column=3, sticky="e")

    # ── Restaurar: event handlers ──────────────────────────────────────────────

    def _on_restore_mode_change(self):
        mode = self.restore_mode.get()
        self.frame_alt_dest.grid_remove()
        self.frame_selection.grid_remove()
        if mode == "alternate":
            self.frame_alt_dest.grid()
        elif mode == "selection":
            self.frame_selection.grid()

    def _browse_restore_src(self):
        p = filedialog.askdirectory(title="Selecionar pasta do backup")
        if not p:
            return
        self.restore_src_entry.delete(0, "end")
        self.restore_src_entry.insert(0, p)
        self._load_manifest(p)

    def _load_manifest(self, backup_dir: str):
        self._corporate_restore_plans = []
        for w in self.corporate_preview_frame.winfo_children():
            w.destroy()
        try:
            plans = discover_corporate_restore_plans(backup_dir)
            if plans:
                self._restore_manifest = None
                self._corporate_restore_plans = [
                    validate_corporate_restore_plan(plan)
                    for plan in plans
                ]
                total_files = sum(plan.manifest.total_files for plan in self._corporate_restore_plans)
                info = (
                    f"✔ backup corporativo carregado — "
                    f"{len(self._corporate_restore_plans)} usuários · "
                    f"{total_files} arquivos"
                )
                self.lbl_manifest_info.configure(text=info, text_color=SUCCESS)
                self._populate_corporate_preview()
                return

            manifest = load_manifest(backup_dir)
            self._restore_manifest = manifest
            info = (
                f"✔ manifest.json carregado — "
                f"{manifest.total_files} arquivos · "
                f"{human_size(manifest.total_size)} · "
                f"backup de {manifest.backup_date[:10]} · "
                f"máquina: {manifest.machine}"
            )
            self.lbl_manifest_info.configure(text=info, text_color=SUCCESS)
            self._populate_selection(manifest)
        except FileNotFoundError:
            self._restore_manifest = None
            self.lbl_manifest_info.configure(
                text="Backup não reconhecido. Selecione a pasta criada pelo BackupTool.", text_color=ERROR_CLR)
        except Exception as e:
            self._restore_manifest = None
            self.lbl_manifest_info.configure(
                text=self._friendly_error(e), text_color=ERROR_CLR)

    def _populate_corporate_preview(self):
        for w in self.corporate_preview_frame.winfo_children():
            w.destroy()
        for plan in self._corporate_restore_plans:
            user = plan.manifest.user or os.path.basename(plan.user_dir)
            status = "✓"
            if plan.missing_files or plan.corrupted_files:
                status = "⚠"
            text = (
                f"{status} {user}\n"
                f"Destino: {plan.destination}\n"
                f"Arquivos: {plan.manifest.total_files} · "
                f"Ausentes: {plan.missing_files} · Corrompidos: {plan.corrupted_files}"
            )
            ctk.CTkLabel(self.corporate_preview_frame, text=text,
                         font=FONT_SMALL, text_color=TEXT_MAIN,
                         justify="left", anchor="w"
                         ).pack(fill="x", padx=8, pady=4)

    def _populate_selection(self, manifest: Manifest):
        for w in self.selection_frame.winfo_children():
            w.destroy()
        self._selection_vars.clear()
        roots = get_manifest_roots(manifest)
        for root in roots:
            var = ctk.BooleanVar(value=True)
            self._selection_vars[root] = var
            ctk.CTkCheckBox(self.selection_frame, text=root,
                            variable=var, text_color=TEXT_MAIN,
                            fg_color=RESTORE_CL, hover_color="#0F766E"
                            ).pack(anchor="w", pady=1)

    def _browse_alt_dest(self):
        p = filedialog.askdirectory(title="Selecionar destino alternativo")
        if p:
            self.restore_alt_entry.delete(0, "end")
            self.restore_alt_entry.insert(0, p)

    def _start_restore(self):
        if self._corporate_restore_plans:
            self._restore_stop = False
            self._restore_started_at = time.time()
            self.btn_restore_start.configure(state="disabled")
            self.btn_restore_stop.configure(state="normal")
            self.lbl_restore_status.configure(text="")
            self.lbl_restore_user.configure(text="Usuário atual\nPreparando...")
            self.lbl_restore_current.configure(text="Arquivo atual\nPreparando...")
            self.lbl_restore_time.configure(text="Tempo\n0s · restante calculando...")
            self._restore_log_clear()
            self.restore_progressbar.set(0)

            threading.Thread(
                target=self._corporate_restore_thread,
                daemon=True,
            ).start()
            return

        if self._restore_manifest is None:
            messagebox.showerror("Sem manifest",
                                 "Selecione uma pasta de backup válida antes de restaurar.")
            return

        mode = self.restore_mode.get()
        conflict = self.conflict_mode.get()
        backup_dir = self.restore_src_entry.get().strip()

        # Destino alternativo
        alternate = ""
        if mode == "alternate":
            alternate = self.restore_alt_entry.get().strip()
            if not alternate:
                messagebox.showerror("Destino necessário",
                                     "Informe a pasta de destino alternativa.")
                return

        # Seleção
        selection: list[str] = []
        if mode == "selection":
            selected_roots = [r for r, v in self._selection_vars.items() if v.get()]
            if not selected_roots:
                messagebox.showwarning("Nada selecionado",
                                       "Selecione ao menos uma pasta para restaurar.")
                return
            # Expande seleção: todos os entries cujo source começa com algum root selecionado
            for entry in self._restore_manifest.files:
                for root in selected_roots:
                    if entry.source.startswith(root):
                        selection.append(entry.source)
                        break

        self._restore_stop = False
        self._restore_started_at = time.time()
        self.btn_restore_start.configure(state="disabled")
        self.btn_restore_stop.configure(state="normal")
        self.lbl_restore_status.configure(text="")
        self.lbl_restore_user.configure(text="Usuário atual\nBackup manual")
        self.lbl_restore_current.configure(text="Arquivo atual\nPreparando...")
        self.lbl_restore_time.configure(text="Tempo\n0s · restante calculando...")
        self._restore_log_clear()
        self.restore_progressbar.set(0)

        threading.Thread(
            target=self._restore_thread,
            args=(backup_dir, mode, selection, alternate, conflict),
            daemon=True,
        ).start()

    def _corporate_restore_thread(self):
        conflict = self.conflict_mode.get()

        def on_progress(user, i, t, path, done, total):
            self.after(0, lambda: self._update_corporate_restore_progress(
                user, i, t, path, done, total))

        def conflict_cb(dest_path: str) -> bool:
            result = [False]
            event = threading.Event()
            def ask():
                ans = messagebox.askyesno(
                    "Conflito",
                    f"O arquivo já existe:\n{dest_path}\n\nSobrescrever?")
                result[0] = ans
                event.set()
            self.after(0, ask)
            event.wait()
            return result[0]

        result = run_corporate_restore(
            self._corporate_restore_plans,
            conflict_mode=conflict,
            conflict_callback=conflict_cb if conflict == "ask" else None,
            on_progress=on_progress,
            stop_flag=lambda: self._restore_stop,
        )
        json_path, csv_path = generate_multi_user_restore_report(
            result,
            output_dir=os.path.join(os.path.dirname(__file__), "logs"),
        )
        self.after(0, lambda: self._corporate_restore_done(result, json_path, csv_path))

    def _stop_restore(self):
        self._restore_stop = True
        self.btn_restore_stop.configure(state="disabled")

    def _restore_thread(self, backup_dir, mode, selection, alternate, conflict):
        def on_progress(i, t, path):
            self.after(0, lambda: self._update_restore_progress(i, t, path))

        def conflict_cb(dest_path: str) -> bool:
            result = [False]
            event = threading.Event()
            def ask():
                ans = messagebox.askyesno(
                    "Conflito",
                    f"O arquivo já existe:\n{dest_path}\n\nSobrescrever?")
                result[0] = ans
                event.set()
            self.after(0, ask)
            event.wait()
            return result[0]

        result = run_restore(
            manifest=self._restore_manifest,
            backup_dir=backup_dir,
            mode=mode,
            selection=selection if mode == "selection" else None,
            alternate_dest=alternate,
            conflict_mode=conflict,
            conflict_callback=conflict_cb if conflict == "ask" else None,
            on_progress=on_progress,
            stop_flag=lambda: self._restore_stop,
        )

        json_path, csv_path = generate_restore_report(
            result,
            self._restore_manifest,
            output_dir=os.path.join(os.path.dirname(__file__), "logs"),
        )

        self.after(0, lambda: self._restore_done(result, json_path, csv_path))

    def _update_restore_progress(self, i, total, path):
        self.restore_progressbar.set(i / total if total else 0)
        self.lbl_restore_counter.configure(text=f"Progresso: {i} / {total} arquivos")
        self.lbl_restore_user.configure(text="Usuário atual\nBackup manual")
        self.lbl_restore_current.configure(text=f"Arquivo atual\n{self._short_path(path)}")
        elapsed = self._format_duration(time.time() - self._restore_started_at)
        remaining = self._estimate_remaining(self._restore_started_at, i, total)
        self.lbl_restore_time.configure(text=f"Tempo\n{elapsed} · restante {remaining}")
        self._restore_log_append(f"[{i:>5}/{total}] {os.path.basename(path)}\n")

    def _update_corporate_restore_progress(self, user, i, total, path, done, overall_total):
        self.restore_progressbar.set(done / overall_total if overall_total else 0)
        self.lbl_restore_counter.configure(text=f"Progresso: {done} / {overall_total} arquivos")
        self.lbl_restore_user.configure(text=f"Usuário atual\n{user}")
        self.lbl_restore_current.configure(text=f"Arquivo atual\n{self._short_path(path)}")
        elapsed = self._format_duration(time.time() - self._restore_started_at)
        remaining = self._estimate_remaining(self._restore_started_at, done, overall_total)
        self.lbl_restore_time.configure(text=f"Tempo\n{elapsed} · restante {remaining}")
        self._restore_log_append(f"[{done:>5}/{overall_total}] {user}: {os.path.basename(path)}\n")

    def _restore_done(self, result: RestoreResult, json_path: str, csv_path: str):
        self.restore_progressbar.set(1)
        self.btn_restore_start.configure(state="normal")
        self.btn_restore_stop.configure(state="disabled")
        self.last_restore_report_path = json_path

        parts = [f"✔ {result.restored} restaurados"]
        if result.overwritten:  parts.append(f"{result.overwritten} sobrescritos")
        if result.skipped:      parts.append(f"{result.skipped} ignorados")
        if result.corrupted:    parts.append(f"{result.corrupted} corrompidos")
        if result.errors:       parts.append(f"{result.errors} erros")

        color = SUCCESS if (result.corrupted + result.errors) == 0 else WARNING
        msg = " · ".join(parts) + f" ({result.elapsed_seconds:.1f}s)"
        self.lbl_restore_status.configure(text=msg, text_color=color)
        self.lbl_restore_time.configure(
            text=f"Tempo\n{self._format_duration(result.elapsed_seconds)} · concluído"
        )

        self._restore_log_append(f"\n{msg}\n")
        self._restore_log_append(f"Relatório JSON : {json_path}\n")
        self._restore_log_append(f"Relatório CSV  : {csv_path}\n")

        if result.corrupted:
            self._restore_log_append("\n── Arquivos corrompidos ──\n")
            for d in result.details:
                if d["status"] == "corrupted":
                    self._restore_log_append(f"  {d['source']}: {d['reason']}\n")

        if result.errors:
            self._restore_log_append("\n── Erros ──\n")
            for d in result.details:
                if d["status"] == "error":
                    self._restore_log_append(f"  {d['source']}: {d['reason']}\n")

    def _corporate_restore_done(self, result, json_path: str, csv_path: str):
        self.restore_progressbar.set(1)
        self.btn_restore_start.configure(state="normal")
        self.btn_restore_stop.configure(state="disabled")
        self.last_restore_report_path = json_path

        parts = [f"✔ {result.restored} restaurados"]
        if result.overwritten:  parts.append(f"{result.overwritten} sobrescritos")
        if result.skipped:      parts.append(f"{result.skipped} ignorados")
        if result.corrupted:    parts.append(f"{result.corrupted} corrompidos")
        if result.errors:       parts.append(f"{result.errors} erros")

        color = SUCCESS if (result.corrupted + result.errors) == 0 else WARNING
        msg = " · ".join(parts) + f" ({result.elapsed_seconds:.1f}s)"
        self.lbl_restore_status.configure(text=msg, text_color=color)
        self.lbl_restore_time.configure(
            text=f"Tempo\n{self._format_duration(result.elapsed_seconds)} · concluído"
        )

        self._restore_log_append(f"\n{msg}\n")
        self._restore_log_append(f"Relatório JSON : {json_path}\n")
        self._restore_log_append(f"Relatório CSV  : {csv_path}\n")

        for item in result.user_results:
            self._restore_log_append(
                f"  {item['user']} → {item['destination']}: "
                f"{item['result'].restored} restaurados, "
                f"{item['result'].corrupted} corrompidos, "
                f"{item['result'].errors} erros\n"
            )

    def _restore_log_append(self, text):
        self.restore_log.configure(state="normal")
        self.restore_log.insert("end", text)
        self.restore_log.see("end")
        self.restore_log.configure(state="disabled")

    def _restore_log_clear(self):
        self.restore_log.configure(state="normal")
        self.restore_log.delete("1.0", "end")
        self.restore_log.configure(state="disabled")

    # ══════════════════════════════════════════
    #  Navegação
    # ══════════════════════════════════════════

    def _current_tab_index(self):
        return TABS.index(self.tabview.get())

    def _go_next(self):
        i = self._current_tab_index()
        if i < len(TABS) - 1:
            self.tabview.set(TABS[i + 1])
            self._on_tab_change()

    def _go_back(self):
        i = self._current_tab_index()
        if i > 0:
            self.tabview.set(TABS[i - 1])
            self._on_tab_change()

    # ══════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════

    def _sync_exclusions(self):
        raw = self.excl_text.get("1.0", "end").strip()
        self.exclusions = [l.strip() for l in raw.splitlines() if l.strip()]


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = BackupApp()
    app.mainloop()