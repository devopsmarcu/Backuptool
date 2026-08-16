#!/usr/bin/env python3
"""
Build script — gera executável portátil via PyInstaller.
Uso:
  python build.py

Saída:
  dist/BackupTool          (Linux)
  dist/BackupTool.exe      (Windows)
"""

import os
import sys
import subprocess
import platform

SYSTEM = platform.system()
NAME   = "BackupTool"

def main():
    # Instala dependências se necessário
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--name={NAME}",
        "--add-data", f"config{os.pathsep}config",
        "--add-data", f"resources{os.pathsep}resources",
        "main.py",
    ]

    if SYSTEM == "Windows":
        # Adiciona ícone se existir
        if os.path.exists("resources/icons/icon.ico"):
            cmd += ["--icon=resources/icons/icon.ico"]
        # Adiciona version info
        if os.path.exists("assets/version_info.txt"):
            cmd += ["--version-file=assets/version_info.txt"]

    subprocess.run(cmd, check=True)
    print(f"\n✔  Build concluído: dist/{NAME}{'exe' if SYSTEM == 'Windows' else ''}")


if __name__ == "__main__":
    main()
