"""
ui/format_utils.py — Pequenas funções de formatação usadas pelas páginas
de execução (Backup e Restaurar).

Portadas sem alteração de comportamento a partir dos métodos homônimos
de `BackupApp` na versão CustomTkinter (`_format_duration`,
`_estimate_remaining`, `_short_path`, `_friendly_error`).
"""

from __future__ import annotations

import time


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins:02d}min"
    if mins:
        return f"{mins}min {secs:02d}s"
    return f"{secs}s"


def estimate_remaining(started_at: float, processed: int, total: int) -> str:
    if not started_at or processed <= 0 or total <= 0:
        return "calculando..."
    elapsed = time.time() - started_at
    remaining = (elapsed / processed) * max(total - processed, 0)
    return format_duration(remaining)


def short_path(path: str, limit: int = 88) -> str:
    if not path:
        return "Aguardando arquivo..."
    return path if len(path) <= limit else "..." + path[-(limit - 3):]


def friendly_error(message) -> str:
    text = str(message)
    low = text.lower()
    if "permission" in low or "permiss" in low or "access" in low:
        return "Acesso negado. Verifique permissões no destino selecionado."
    if "no space" in low or "space" in low:
        return "Espaço insuficiente no destino selecionado."
    if "manifest" in low:
        return "Não foi possível validar o backup selecionado."
    return text
