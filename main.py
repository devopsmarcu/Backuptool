"""
main.py — BackupTool GUI (CustomTkinter)

Abas:
  1 · Origem      — paths e exclusões
  3 · Destino     — HD externo / pasta de rede
  4 · Resumo      — scan pré-backup
  5 · Progresso   — execução do backup
  6 · Restaurar   — restauração a partir de manifest.json
"""

import os
import platform
import socket
import threading
import tkinter as tk
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
#  Tema
# ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT     = "#3B82F6"
BG_DARK    = "#0F172A"
BG_CARD    = "#1E293B"
BG_INPUT   = "#334155"
TEXT_MAIN  = "#F1F5F9"
TEXT_MUTED = "#94A3B8"
SUCCESS    = "#22C55E"
WARNING    = "#F59E0B"
ERROR_CLR  = "#EF4444"
RESTORE_CL = "#A78BFA"   # violeta — identifica visualmente a aba de restauração

FONT_TITLE = ("Inter", 20, "bold")
FONT_LABEL = ("Inter", 12)
FONT_SMALL = ("Inter", 11)
FONT_MONO  = ("JetBrains Mono", 10) if platform.system() != "Darwin" else ("Menlo", 10)

TABS = ["1 · Origem", "2 · Usuários", "3 · Destino", "4 · Resumo", "5 · Progresso", "6 · Restaurar"]


# ─────────────────────────────────────────────
#  App principal
# ─────────────────────────────────────────────
class BackupApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BackupTool — Backup & Restauração Pré-Formatação")
        self.geometry("960x720")
        self.minsize(860, 620)
        self.configure(fg_color=BG_DARK)

        # ── Estado backup ──
        self.paths       = get_default_paths()
        self.exclusions  = list(DEFAULT_EXCLUSIONS)
        self.excl_exts   = list(DEFAULT_EXCLUDED_EXTENSIONS)
        self.destination = ""
        self.scanned     = []
        self.scanned_by_user = {}
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
        self._build_body()
        self._build_footer()

    # ══════════════════════════════════════════
    #  Layout base
    # ══════════════════════════════════════════

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="💾  BackupTool",
                     font=FONT_TITLE, text_color=TEXT_MAIN
                     ).pack(side="left", padx=24, pady=16)
        ctk.CTkLabel(hdr, text=f"Máquina: {socket.gethostname()}",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(side="right", padx=24)

    def _build_body(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=BG_CARD,
            segmented_button_fg_color=BG_INPUT,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT,
            text_color=TEXT_MAIN,
            corner_radius=12,
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(12, 4))
        for t in TABS:
            self.tabview.add(t)

        self._build_tab_origem()
        self._build_tab_usuarios()
        self._build_tab_destino()
        self._build_tab_resumo()
        self._build_tab_progresso()
        self._build_tab_restaurar()

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=56)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)
        self.btn_back = ctk.CTkButton(
            foot, text="← Voltar", width=120,
            fg_color=BG_INPUT, hover_color=BG_INPUT,
            text_color=TEXT_MUTED, command=self._go_back)
        self.btn_back.pack(side="left", padx=16, pady=10)
        self.btn_next = ctk.CTkButton(
            foot, text="Próximo →", width=160,
            fg_color=ACCENT, hover_color="#2563EB",
            text_color="white", command=self._go_next)
        self.btn_next.pack(side="right", padx=16, pady=10)

    # ══════════════════════════════════════════
    #  Aba 1 — Origem
    # ══════════════════════════════════════════

    def _build_tab_origem(self):
        tab = self.tabview.tab("1 · Origem")
        ctk.CTkLabel(tab, text="Pastas para backup",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(8, 2))
        ctk.CTkLabel(tab,
                     text="Pré-definidas com base no sistema. Adicione ou remova conforme necessário.",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=4, pady=(0, 8))

        self.paths_frame = ctk.CTkScrollableFrame(tab, fg_color=BG_INPUT,
                                                   corner_radius=8, height=180)
        self.paths_frame.pack(fill="x", padx=4, pady=(0, 8))
        self._refresh_paths_list()

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=(0, 12))
        ctk.CTkButton(row, text="+ Adicionar pasta", fg_color=ACCENT,
                      hover_color="#2563EB", command=self._add_path, width=160
                      ).pack(side="left")

        ctk.CTkLabel(tab, text="Exclusões",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(0, 2))
        ctk.CTkLabel(tab, text="Pastas e extensões ignoradas durante o scan.",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=4, pady=(0, 6))
        self.excl_text = ctk.CTkTextbox(tab, height=90, font=FONT_MONO,
                                        fg_color=BG_INPUT, text_color=TEXT_MAIN)
        self.excl_text.pack(fill="x", padx=4)
        self.excl_text.insert("end", "\n".join(self.exclusions))

    def _refresh_paths_list(self):
        for w in self.paths_frame.winfo_children():
            w.destroy()
        for p in self.paths:
            row = ctk.CTkFrame(self.paths_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=p, font=FONT_SMALL,
                         text_color=TEXT_MAIN, anchor="w"
                         ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="✕", width=28, height=24,
                          fg_color=ERROR_CLR, hover_color="#B91C1C",
                          text_color="white",
                          command=lambda path=p: self._remove_path(path)
                          ).pack(side="right", padx=(4, 0))

    def _add_path(self):
        p = filedialog.askdirectory(title="Selecionar pasta")
        if p and p not in self.paths:
            self.paths.append(p)
            self._refresh_paths_list()

    def _remove_path(self, path):
        self.paths.remove(path)
        self._refresh_paths_list()

    # ══════════════════════════════════════════
    #  Aba 2 — Usuários
    # ══════════════════════════════════════════

    def _build_tab_usuarios(self):
        tab = self.tabview.tab("2 · Usuários")
        ctk.CTkLabel(tab, text="Usuários encontrados",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(8, 2))
        ctk.CTkLabel(tab,
                     text="Selecione os perfis corporativos que serão incluídos no backup.",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=4, pady=(0, 8))

        self.users_frame = ctk.CTkScrollableFrame(tab, fg_color=BG_INPUT,
                                                  corner_radius=8, height=300)
        self.users_frame.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkButton(row, text="Selecionar Todos",
                      fg_color=ACCENT, hover_color="#2563EB",
                      command=self._select_all_users, width=150
                      ).pack(side="left")
        ctk.CTkButton(row, text="Atualizar Usuários",
                      fg_color=BG_INPUT, hover_color=BG_CARD,
                      text_color=TEXT_MUTED,
                      command=self._refresh_users, width=150
                      ).pack(side="left", padx=8)
        self.lbl_users_status = ctk.CTkLabel(row, text="",
                                             font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_users_status.pack(side="right")

        self._refresh_users()

    def _refresh_users(self):
        for w in self.users_frame.winfo_children():
            w.destroy()
        self.user_profiles = detect_user_profiles()
        self._user_vars.clear()
        if not self.user_profiles:
            ctk.CTkLabel(self.users_frame,
                         text="Nenhum perfil de usuário corporativo encontrado.",
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=8)
            self.lbl_users_status.configure(text="0 usuários selecionados")
            return
        for profile in self.user_profiles:
            var = ctk.BooleanVar(value=True)
            self._user_vars[profile.username] = var
            ctk.CTkCheckBox(self.users_frame,
                            text=f"{profile.username}  —  {profile.path}",
                            variable=var, text_color=TEXT_MAIN,
                            fg_color=ACCENT, hover_color="#2563EB",
                            command=self._update_selected_users
                            ).pack(anchor="w", padx=8, pady=3)
        self._update_selected_users()

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
        ctk.CTkLabel(tab, text="Onde salvar o backup",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(8, 2))

        ctk.CTkLabel(tab, text="Dispositivos detectados",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=4, pady=(6, 2))
        self.drives_frame = ctk.CTkScrollableFrame(tab, fg_color=BG_INPUT,
                                                    corner_radius=8, height=130)
        self.drives_frame.pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkButton(tab, text="↺  Atualizar dispositivos",
                      fg_color=BG_INPUT, hover_color=BG_CARD,
                      text_color=TEXT_MUTED, width=180,
                      command=self._refresh_drives
                      ).pack(anchor="w", padx=4, pady=(0, 12))
        self._refresh_drives()

        ctk.CTkLabel(tab, text="Ou digitar caminho manualmente",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(0, 4))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=4)
        self.dest_entry = ctk.CTkEntry(
            row, placeholder_text=r"Ex: \\servidor\backup  ou  /mnt/externo",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_INPUT)
        self.dest_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="Procurar", width=100,
                      fg_color=ACCENT, hover_color="#2563EB",
                      command=self._browse_dest
                      ).pack(side="right", padx=(8, 0))
        self.lbl_dest_status = ctk.CTkLabel(tab, text="",
                                             font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_dest_status.pack(anchor="w", padx=4, pady=(6, 0))

    def _refresh_drives(self):
        for w in self.drives_frame.winfo_children():
            w.destroy()
        drives = detect_external_drives()
        if not drives:
            ctk.CTkLabel(self.drives_frame,
                         text="Nenhum dispositivo externo detectado.",
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=8)
            return
        for d in drives:
            row = ctk.CTkFrame(self.drives_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row,
                         text=f"  {d['label']}  [{d['type']}]  —  {d['path']}",
                         font=FONT_SMALL, text_color=TEXT_MAIN, anchor="w"
                         ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Usar", width=60,
                          fg_color=SUCCESS, hover_color="#16A34A",
                          text_color="white",
                          command=lambda path=d["path"]: self._select_drive(path)
                          ).pack(side="right", padx=(4, 0))

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
    #  Aba 3 — Resumo
    # ══════════════════════════════════════════

    def _build_tab_resumo(self):
        tab = self.tabview.tab("4 · Resumo")
        ctk.CTkLabel(tab, text="Revisão antes do backup",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(8, 2))
        self.resumo_box = ctk.CTkTextbox(tab, font=FONT_MONO,
                                          fg_color=BG_INPUT, text_color=TEXT_MAIN,
                                          state="disabled")
        self.resumo_box.pack(fill="both", expand=True, padx=4, pady=(4, 8))
        self.btn_scan = ctk.CTkButton(tab, text="🔍  Escanear agora",
                                       fg_color=ACCENT, hover_color="#2563EB",
                                       command=self._start_scan)
        self.btn_scan.pack(pady=(0, 4))

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
        self._set_resumo("⏳ Escaneando arquivos, aguarde...\n")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        count = [0]
        def on_file(path):
            count[0] += 1
            if count[0] % 50 == 0:
                self.after(0, lambda: self._set_resumo(
                    f"⏳ Encontrados: {count[0]} arquivos...\n"))

        self.scanned_by_user = {}
        if self.selected_profiles:
            self.scanned = []
            lines = ["✔  Scan concluído\n", f"   Destino              : {self.destination}", ""]
            total_b = 0
            for profile in self.selected_profiles:
                entries = scan_profile_path(profile.path, self.exclusions, self.excl_exts, on_file)
                self.scanned_by_user[profile.username] = entries
                self.scanned.extend(entries)
                user_total = total_size(entries)
                total_b += user_total
                lines.append(f"   {profile.username}: {len(entries)} arquivos · {human_size(user_total)}")
            lines.extend([
                "",
                f"   Arquivos encontrados : {len(self.scanned)}",
                f"   Tamanho total        : {human_size(total_b)}",
                "", "── Usuários incluídos ──",
            ])
            lines.extend([f"  {p.username}  —  {p.path}" for p in self.selected_profiles])
        else:
            self.scanned = scan_paths(self.paths, self.exclusions, self.excl_exts, on_file)
            total_b = total_size(self.scanned)
            lines = [
                "✔  Scan concluído\n",
                f"   Arquivos encontrados : {len(self.scanned)}",
                f"   Tamanho total        : {human_size(total_b)}",
                f"   Destino              : {self.destination}",
                "", "── Pastas incluídas ──",
            ] + [f"  {p}" for p in self.paths]

        lines += [
            "", "── Primeiros 20 arquivos ──",
        ] + [f"  {e.relative_path}  ({human_size(e.size)})" for e in self.scanned[:20]]
        if len(self.scanned) > 20:
            lines.append(f"  ... e mais {len(self.scanned) - 20} arquivos")

        self.after(0, lambda: self._set_resumo("\n".join(lines)))
        self.after(0, lambda: self.btn_scan.configure(
            state="normal", text="🔍  Escanear novamente"))

    def _set_resumo(self, text):
        self.resumo_box.configure(state="normal")
        self.resumo_box.delete("1.0", "end")
        self.resumo_box.insert("end", text)
        self.resumo_box.configure(state="disabled")

    # ══════════════════════════════════════════
    #  Aba 4 — Progresso (Backup)
    # ══════════════════════════════════════════

    def _build_tab_progresso(self):
        tab = self.tabview.tab("5 · Progresso")
        ctk.CTkLabel(tab, text="Executando backup",
                     font=("Inter", 13, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=4, pady=(8, 2))

        self.lbl_current = ctk.CTkLabel(tab, text="Aguardando início...",
                                         font=FONT_SMALL, text_color=TEXT_MUTED,
                                         anchor="w", wraplength=880)
        self.lbl_current.pack(fill="x", padx=4, pady=(4, 2))

        self.progressbar = ctk.CTkProgressBar(tab, height=16,
                                               fg_color=BG_INPUT, progress_color=ACCENT)
        self.progressbar.pack(fill="x", padx=4, pady=(2, 4))
        self.progressbar.set(0)

        self.lbl_counter = ctk.CTkLabel(tab, text="0 / 0",
                                         font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_counter.pack(anchor="e", padx=4)

        self.log_box = ctk.CTkTextbox(tab, font=FONT_MONO,
                                       fg_color=BG_INPUT, text_color=TEXT_MAIN,
                                       state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=(0, 4))
        self.btn_start = ctk.CTkButton(row, text="▶  Iniciar backup",
                                        fg_color=SUCCESS, hover_color="#16A34A",
                                        command=self._start_backup, width=160)
        self.btn_start.pack(side="left")
        self.btn_stop = ctk.CTkButton(row, text="⏹  Parar",
                                       fg_color=ERROR_CLR, hover_color="#B91C1C",
                                       command=self._stop_backup, width=100,
                                       state="disabled")
        self.btn_stop.pack(side="left", padx=8)
        self.lbl_status_final = ctk.CTkLabel(row, text="",
                                              font=("Inter", 12, "bold"),
                                              text_color=TEXT_MUTED)
        self.lbl_status_final.pack(side="right")

    def _start_backup(self):
        if not self.scanned:
            messagebox.showwarning("Scan necessário",
                                   "Execute o scan na aba Resumo antes de iniciar o backup.")
            return
        self._stop_flag = False
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status_final.configure(text="")
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
        self.progressbar.set(i / total)
        self.lbl_counter.configure(text=f"{i} / {total}")
        short = path if len(path) < 90 else "..." + path[-87:]
        self.lbl_current.configure(text=short)
        self._log_append(f"[{i:>5}/{total}] {path}\n")

    def _update_user_progress(self, user, i, total, path, copied, overall_total):
        self.progressbar.set(copied / overall_total if overall_total else 0)
        self.lbl_counter.configure(text=f"{copied} / {overall_total}")
        short = path if len(path) < 90 else "..." + path[-87:]
        self.lbl_current.configure(text=f"Usuário: {user} | Arquivo: {short}")
        self._log_append(f"[{copied:>5}/{overall_total}] {user}: {path}\n")

    def _backup_done(self, result, report_path):
        self.progressbar.set(1)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

        if result.errors == 0:
            color, msg = SUCCESS, f"✔ Concluído — {result.copied} arquivos copiados"
        else:
            color = WARNING
            msg = f"⚠ Concluído com erros — {result.copied} copiados, {result.errors} erros"

        self.lbl_status_final.configure(text=msg, text_color=color)
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

        if result.errors == 0:
            color, msg = SUCCESS, f"✔ Concluído — {result.copied} arquivos copiados"
        else:
            color = WARNING
            msg = f"⚠ Concluído com erros — {result.copied} copiados, {result.errors} erros"

        self.lbl_status_final.configure(text=msg, text_color=color)
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
    #  Aba 5 — Restaurar
    # ══════════════════════════════════════════

    def _build_tab_restaurar(self):
        tab = self.tabview.tab("6 · Restaurar")

        # ── Seção: Selecionar backup ──
        ctk.CTkLabel(tab, text="Restaurar Backup",
                     font=("Inter", 13, "bold"), text_color=RESTORE_CL
                     ).pack(anchor="w", padx=4, pady=(8, 2))
        ctk.CTkLabel(tab, text="Selecione a pasta de backup gerada pelo BackupTool.",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=4, pady=(0, 6))

        row_src = ctk.CTkFrame(tab, fg_color="transparent")
        row_src.pack(fill="x", padx=4, pady=(0, 4))
        self.restore_src_entry = ctk.CTkEntry(
            row_src, placeholder_text="Pasta do backup (contém manifest.json)",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_INPUT)
        self.restore_src_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row_src, text="Procurar", width=100,
                      fg_color=RESTORE_CL, hover_color="#7C3AED",
                      command=self._browse_restore_src
                      ).pack(side="right", padx=(8, 0))

        self.lbl_manifest_info = ctk.CTkLabel(tab, text="",
                                               font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_manifest_info.pack(anchor="w", padx=4, pady=(2, 8))

        self.corporate_preview_frame = ctk.CTkScrollableFrame(
            tab, fg_color=BG_INPUT, corner_radius=8, height=110)
        self.corporate_preview_frame.pack(fill="x", padx=4, pady=(0, 8))

        # ── Dois painéis lado a lado: Modo + Conflito ──
        panels = ctk.CTkFrame(tab, fg_color="transparent")
        panels.pack(fill="x", padx=4, pady=(0, 8))

        # Modo de restauração
        pane_mode = ctk.CTkFrame(panels, fg_color=BG_INPUT, corner_radius=8)
        pane_mode.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(pane_mode, text="Modo de restauração",
                     font=("Inter", 11, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=10, pady=(8, 4))

        self.restore_mode = ctk.StringVar(value="all")
        for val, label in [
            ("all",       "Restaurar tudo"),
            ("selection", "Restaurar seleção"),
            ("alternate", "Restaurar para outro local"),
        ]:
            ctk.CTkRadioButton(pane_mode, text=label, variable=self.restore_mode,
                               value=val, text_color=TEXT_MAIN,
                               fg_color=RESTORE_CL, hover_color="#7C3AED",
                               command=self._on_restore_mode_change
                               ).pack(anchor="w", padx=12, pady=2)
        pane_mode.pack_configure(pady=(0, 0))

        # Modo de conflito
        pane_conf = ctk.CTkFrame(panels, fg_color=BG_INPUT, corner_radius=8)
        pane_conf.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(pane_conf, text="Conflitos",
                     font=("Inter", 11, "bold"), text_color=TEXT_MAIN
                     ).pack(anchor="w", padx=10, pady=(8, 4))

        self.conflict_mode = ctk.StringVar(value="overwrite")
        for val, label in [
            ("overwrite", "Sobrescrever"),
            ("ask",       "Perguntar"),
            ("ignore",    "Ignorar"),
        ]:
            ctk.CTkRadioButton(pane_conf, text=label, variable=self.conflict_mode,
                               value=val, text_color=TEXT_MAIN,
                               fg_color=RESTORE_CL, hover_color="#7C3AED",
                               ).pack(anchor="w", padx=12, pady=2)

        # ── Destino alternativo (oculto por padrão) ──
        self.frame_alt_dest = ctk.CTkFrame(tab, fg_color="transparent")
        ctk.CTkLabel(self.frame_alt_dest, text="Pasta de destino alternativa",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", pady=(0, 2))
        row_alt = ctk.CTkFrame(self.frame_alt_dest, fg_color="transparent")
        row_alt.pack(fill="x")
        self.restore_alt_entry = ctk.CTkEntry(
            row_alt, placeholder_text="Ex: D:\\Recuperacao  ou  /mnt/recuperacao",
            fg_color=BG_INPUT, text_color=TEXT_MAIN, border_color=BG_INPUT)
        self.restore_alt_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row_alt, text="Procurar", width=100,
                      fg_color=RESTORE_CL, hover_color="#7C3AED",
                      command=self._browse_alt_dest
                      ).pack(side="right", padx=(8, 0))

        # ── Seleção de arquivos (oculto por padrão) ──
        self.frame_selection = ctk.CTkFrame(tab, fg_color="transparent")
        ctk.CTkLabel(self.frame_selection, text="Selecione quais pastas restaurar",
                     font=FONT_SMALL, text_color=TEXT_MUTED
                     ).pack(anchor="w", pady=(0, 2))
        self.selection_frame = ctk.CTkScrollableFrame(
            self.frame_selection, fg_color=BG_INPUT, corner_radius=8, height=80)
        self.selection_frame.pack(fill="x")
        self._selection_vars: dict[str, ctk.BooleanVar] = {}

        # ── Barra de progresso da restauração ──
        self.lbl_restore_current = ctk.CTkLabel(
            tab, text="", font=FONT_SMALL, text_color=TEXT_MUTED,
            anchor="w", wraplength=880)
        self.lbl_restore_current.pack(fill="x", padx=4, pady=(4, 2))

        self.restore_progressbar = ctk.CTkProgressBar(
            tab, height=14, fg_color=BG_INPUT, progress_color=RESTORE_CL)
        self.restore_progressbar.pack(fill="x", padx=4, pady=(0, 2))
        self.restore_progressbar.set(0)

        self.lbl_restore_counter = ctk.CTkLabel(
            tab, text="", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_restore_counter.pack(anchor="e", padx=4)

        self.restore_log = ctk.CTkTextbox(
            tab, font=FONT_MONO, fg_color=BG_INPUT, text_color=TEXT_MAIN,
            state="disabled", height=100)
        self.restore_log.pack(fill="both", expand=True, padx=4, pady=(4, 4))

        # ── Botões ──
        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=4, pady=(0, 4))

        self.btn_restore_start = ctk.CTkButton(
            btn_row, text="♻  Iniciar restauração",
            fg_color=RESTORE_CL, hover_color="#7C3AED",
            command=self._start_restore, width=180)
        self.btn_restore_start.pack(side="left")

        self.btn_restore_stop = ctk.CTkButton(
            btn_row, text="⏹  Parar",
            fg_color=ERROR_CLR, hover_color="#B91C1C",
            command=self._stop_restore, width=100, state="disabled")
        self.btn_restore_stop.pack(side="left", padx=8)

        self.lbl_restore_status = ctk.CTkLabel(
            btn_row, text="", font=("Inter", 12, "bold"), text_color=TEXT_MUTED)
        self.lbl_restore_status.pack(side="right")

    # ── Restaurar: event handlers ──────────────────────────────────────────────

    def _on_restore_mode_change(self):
        mode = self.restore_mode.get()
        self.frame_alt_dest.pack_forget()
        self.frame_selection.pack_forget()
        if mode == "alternate":
            self.frame_alt_dest.pack(fill="x", padx=4, pady=(0, 6))
        elif mode == "selection":
            self.frame_selection.pack(fill="x", padx=4, pady=(0, 6))

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
                text="✗ manifest.json não encontrado nesta pasta.", text_color=ERROR_CLR)
        except Exception as e:
            self._restore_manifest = None
            self.lbl_manifest_info.configure(
                text=f"✗ Erro ao ler manifest: {e}", text_color=ERROR_CLR)

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
                            fg_color=RESTORE_CL, hover_color="#7C3AED"
                            ).pack(anchor="w", pady=1)

    def _browse_alt_dest(self):
        p = filedialog.askdirectory(title="Selecionar destino alternativo")
        if p:
            self.restore_alt_entry.delete(0, "end")
            self.restore_alt_entry.insert(0, p)

    def _start_restore(self):
        if self._corporate_restore_plans:
            self._restore_stop = False
            self.btn_restore_start.configure(state="disabled")
            self.btn_restore_stop.configure(state="normal")
            self.lbl_restore_status.configure(text="")
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
        self.btn_restore_start.configure(state="disabled")
        self.btn_restore_stop.configure(state="normal")
        self.lbl_restore_status.configure(text="")
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
        self.lbl_restore_counter.configure(text=f"{i} / {total}")
        short = path if len(path) < 90 else "..." + path[-87:]
        self.lbl_restore_current.configure(text=f"Restaurando: {short}")
        self._restore_log_append(f"[{i:>5}/{total}] {path}\n")

    def _update_corporate_restore_progress(self, user, i, total, path, done, overall_total):
        self.restore_progressbar.set(done / overall_total if overall_total else 0)
        self.lbl_restore_counter.configure(text=f"{done} / {overall_total}")
        short = path if len(path) < 90 else "..." + path[-87:]
        self.lbl_restore_current.configure(text=f"Usuário: {user} | Arquivo: {short}")
        self._restore_log_append(f"[{done:>5}/{overall_total}] {user}: {path}\n")

    def _restore_done(self, result: RestoreResult, json_path: str, csv_path: str):
        self.restore_progressbar.set(1)
        self.btn_restore_start.configure(state="normal")
        self.btn_restore_stop.configure(state="disabled")

        parts = [f"✔ {result.restored} restaurados"]
        if result.overwritten:  parts.append(f"{result.overwritten} sobrescritos")
        if result.skipped:      parts.append(f"{result.skipped} ignorados")
        if result.corrupted:    parts.append(f"{result.corrupted} corrompidos")
        if result.errors:       parts.append(f"{result.errors} erros")

        color = SUCCESS if (result.corrupted + result.errors) == 0 else WARNING
        msg = " · ".join(parts) + f" ({result.elapsed_seconds:.1f}s)"
        self.lbl_restore_status.configure(text=msg, text_color=color)

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

        parts = [f"✔ {result.restored} restaurados"]
        if result.overwritten:  parts.append(f"{result.overwritten} sobrescritos")
        if result.skipped:      parts.append(f"{result.skipped} ignorados")
        if result.corrupted:    parts.append(f"{result.corrupted} corrompidos")
        if result.errors:       parts.append(f"{result.errors} erros")

        color = SUCCESS if (result.corrupted + result.errors) == 0 else WARNING
        msg = " · ".join(parts) + f" ({result.elapsed_seconds:.1f}s)"
        self.lbl_restore_status.configure(text=msg, text_color=color)

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

    def _go_back(self):
        i = self._current_tab_index()
        if i > 0:
            self.tabview.set(TABS[i - 1])

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
