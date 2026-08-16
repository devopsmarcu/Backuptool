import os
import sys
from pathlib import Path

def get_app_dir() -> Path:
    """
    Returns the directory where the application is installed/located.
    - In PyInstaller mode: The directory containing the .exe.
    - In Python mode: The project root directory.
    """
    if getattr(sys, "frozen", False):
        # If bundled by PyInstaller, sys.executable is the path to the .exe
        return Path(os.path.dirname(sys.executable)).resolve()
    else:
        # If running as a script, return the project root (one level up from config/)
        return Path(__file__).resolve().parent.parent

def get_resource_path(relative_path: str) -> Path:
    """
    Returns the absolute path to a resource.
    - In PyInstaller mode: Resolves to the temporary _MEIPASS folder.
    - In Python mode: Resolves relative to the project root.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    else:
        # Project root directory
        base_path = get_app_dir()

    return (base_path / relative_path).resolve()

def get_logs_dir() -> Path:
    """Returns the path to the logs directory in the application folder."""
    return get_app_dir() / "logs"

def get_config_path(filename: str = ".env") -> Path:
    """Returns the path to a configuration file in the application folder."""
    return get_app_dir() / filename
