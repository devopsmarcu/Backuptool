import os
import platform
import subprocess
import shutil
from typing import List, Dict, Tuple, Optional


SYSTEM = platform.system()


def detect_external_drives() -> List[Dict[str, str]]:
    drives = []
    if SYSTEM == "Windows":
        import string
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if drive_type in (2, 3, 4):
                    try:
                        total = shutil.disk_usage(drive).total
                        label = _get_windows_label(letter)
                        label_str = f" ({label})" if label else ""
                        drives.append({
                            "path": drive,
                            "label": f"{letter}:{label_str}",
                            "type": {2: "Removível", 3: "Local", 4: "Rede"}.get(drive_type, ""),
                        })
                    except Exception:
                        pass
            bitmask >>= 1
    else:
        try:
            result = subprocess.run(
                ["lsblk", "-o", "NAME,MOUNTPOINT,LABEL,TYPE", "--noheadings"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    mountpoint = parts[1]
                    label = parts[2] if len(parts) > 2 else ""
                    if mountpoint.startswith("/media") or mountpoint.startswith("/mnt"):
                        drives.append({
                            "path": mountpoint,
                            "label": label or os.path.basename(mountpoint),
                            "type": "Removível",
                        })
        except Exception:
            pass
    return drives


def _get_windows_label(letter: str) -> str:
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.kernel32.GetVolumeInformationW(
            f"{letter}:\\", buf, 256, None, None, None, None, 0
        )
        return buf.value
    except Exception:
        return ""


def check_disk_space(path: str, required_bytes: int) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Check if there's enough space on the disk.
    Returns (has_space, free_bytes, total_bytes)
    """
    try:
        usage = shutil.disk_usage(path)
        free = usage.free
        total = usage.total
        has_space = free >= required_bytes
        return has_space, free, total
    except Exception:
        return False, None, None


def validate_destination(path: str) -> tuple[bool, str]:
    if not path or not path.strip():
        return False, "Nenhum destino selecionado."
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            return False, f"Não foi possível criar o diretório: {e}"
    if not os.access(path, os.W_OK):
        return False, "Sem permissão de escrita no destino."
    return True, "OK"
