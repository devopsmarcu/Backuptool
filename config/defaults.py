import os
import platform

SYSTEM = platform.system()  # 'Windows' or 'Linux'


def get_default_paths():
    paths = []
    if SYSTEM == "Windows":
        base = os.environ.get("USERPROFILE", f"C:\\Users\\{os.environ.get('USERNAME', 'Usuario')}")
        candidates = [
            os.path.join(base, "Desktop"),
            os.path.join(base, "Documents"),
            os.path.join(base, "Downloads"),
            os.path.join(base, "Pictures"),
            os.path.join(base, "Videos"),
            os.path.join(base, "Music"),
        ]
    else:
        base = os.environ.get("HOME", f"/home/{os.environ.get('USER', 'usuario')}")
        candidates = [
            os.path.join(base, "Desktop"),
            os.path.join(base, "Documentos"),
            os.path.join(base, "Documents"),
            os.path.join(base, "Downloads"),
            os.path.join(base, "Imagens"),
            os.path.join(base, "Pictures"),
            os.path.join(base, "Vídeos"),
            os.path.join(base, "Videos"),
            os.path.join(base, "Músicas"),
            os.path.join(base, "Music"),
        ]

    for p in candidates:
        if os.path.exists(p):
            paths.append(p)

    return paths


DEFAULT_EXCLUSIONS = [
    # Cache e temporários
    "node_modules",
    ".git",
    "__pycache__",
    ".cache",
    "Temp",
    "temp",
    "tmp",
    ".tmp",
    # Windows específico
    "AppData\\Local\\Temp",
    "AppData\\Local\\Microsoft\\Windows\\INetCache",
    "AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache",
    # Linux específico
    ".local/share/Trash",
    ".thumbnails",
    ".mozilla/firefox",
    # Builds e artefatos
    "dist",
    "build",
    ".next",
    "venv",
    ".venv",
    "env",
]

DEFAULT_EXCLUDED_EXTENSIONS = [
    ".tmp", ".temp", ".log", ".bak",
    ".DS_Store", "Thumbs.db",
]
