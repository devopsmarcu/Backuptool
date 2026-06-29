import os
import platform
from dataclasses import dataclass
from typing import List


SYSTEM = platform.system()

WINDOWS_IGNORED_PROFILES = {
    "public",
    "default",
    "default user",
    "all users",
    "defaultapppool",
    "wdagutilityaccount",
}

WINDOWS_SERVICE_PREFIXES = (
    "localservice",
    "networkservice",
    "systemprofile",
    "service",
    "svc_",
)

LINUX_IGNORED_USERS = {
    "bin",
    "daemon",
    "adm",
    "lp",
    "sync",
    "shutdown",
    "halt",
    "mail",
    "operator",
    "games",
    "ftp",
    "nobody",
    "systemd-network",
    "systemd-resolve",
    "messagebus",
    "polkitd",
}


@dataclass
class UserProfile:
    username: str
    path: str


def get_profiles_root() -> str:
    if SYSTEM == "Windows":
        return r"C:\Users"
    return "/home"


def is_ignored_profile(name: str, path: str) -> bool:
    normalized = name.strip().lower()
    if not normalized:
        return True
    if SYSTEM == "Windows":
        if normalized in WINDOWS_IGNORED_PROFILES:
            return True
        if normalized.endswith(".tmp") or normalized.startswith("temp"):
            return True
        if any(normalized.startswith(prefix) for prefix in WINDOWS_SERVICE_PREFIXES):
            return True
        return False
    if normalized in LINUX_IGNORED_USERS:
        return True
    return normalized.startswith(".")


def detect_user_profiles(root: str | None = None) -> List[UserProfile]:
    profiles_root = root or get_profiles_root()
    profiles: List[UserProfile] = []
    if not os.path.isdir(profiles_root):
        return profiles

    for name in sorted(os.listdir(profiles_root), key=str.lower):
        path = os.path.join(profiles_root, name)
        if not os.path.isdir(path):
            continue
        if is_ignored_profile(name, path):
            continue
        profiles.append(UserProfile(username=name, path=path))
    return profiles


def corporate_restore_destination(username: str) -> str:
    if SYSTEM == "Windows":
        return os.path.join(r"C:\Users", f"{username}.SANTACASABA")
    return os.path.join("/home", f"{username}.SANTACASABA")
