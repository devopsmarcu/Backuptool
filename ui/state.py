"""
ui/state.py — Estado compartilhado da aplicação.

Substitui os atributos que, na versão CustomTkinter, viviam soltos em
`BackupApp` (self.paths, self.scanned, self.destination, ...). Nenhuma
regra de negócio vive aqui: é apenas o "Model" que as páginas leem e
escrevem, para não precisarem se conhecer diretamente.

Os nomes dos campos foram mantidos idênticos aos da versão CustomTkinter
para que a integração com core/ e config/ (não alterados) continue igual.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Optional

from config.defaults import get_default_paths, DEFAULT_EXCLUSIONS, DEFAULT_EXCLUDED_EXTENSIONS
from core.manifest import Manifest
from core.profiles import UserProfile


@dataclass
class AppState:
    # Origem
    paths: list[str] = field(default_factory=get_default_paths)
    exclusions: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUSIONS))
    excl_exts: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_EXTENSIONS))

    # Usuários
    user_profiles: list[UserProfile] = field(default_factory=list)
    selected_profiles: list[UserProfile] = field(default_factory=list)

    # Destino
    destination: str = ""

    # Scan / resumo
    scanned: list = field(default_factory=list)
    scanned_by_user: dict = field(default_factory=dict)

    # Backup
    last_backup_dir: str = ""
    last_report_path: str = ""

    # Restauração
    restore_manifest: Optional[Manifest] = None
    corporate_restore_plans: list = field(default_factory=list)
    last_restore_report_path: str = ""

    # Sessão
    technician: str = field(default_factory=socket.gethostname)

    def reset_for_new_run(self):
        """Equivalente ao antigo `_restart_process` (apenas o estado, sem UI)."""
        self.scanned = []
        self.scanned_by_user = {}
        self.destination = ""
        self.last_backup_dir = ""
        self.last_report_path = ""
        self.last_restore_report_path = ""
        self.restore_manifest = None
        self.corporate_restore_plans = []
