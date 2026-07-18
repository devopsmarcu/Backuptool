import platform
import ctypes
from typing import Optional


SYSTEM = platform.system()


class ProfileError(Exception):
    pass


def is_admin() -> bool:
    if SYSTEM != "Windows":
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _lookup_sid(username: str, domain: str = "") -> str:
    if SYSTEM != "Windows":
        raise ProfileError("Only available on Windows")
    
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.windll.kernel32
    
    # LookupAccountNameW parameters
    account_name = f"{domain}\\{username}" if domain else username
    cbSid = ctypes.c_ulong(0)
    cbReferencedDomainName = ctypes.c_ulong(0)
    peUse = ctypes.c_ulong()
    
    # First call to get buffer sizes
    advapi32.LookupAccountNameW(
        None,
        account_name,
        None,
        ctypes.byref(cbSid),
        None,
        ctypes.byref(cbReferencedDomainName),
        ctypes.byref(peUse),
    )
    last_err = ctypes.get_last_error()
    if last_err != 122:  # ERROR_INSUFFICIENT_BUFFER
        raise ProfileError(f"Failed to get account info (error: {last_err})")
    
    # Allocate buffers
    sid = ctypes.create_string_buffer(cbSid.value)
    referenced_domain_name = ctypes.create_unicode_buffer(cbReferencedDomainName.value)
    
    # Second call to get actual data
    success = advapi32.LookupAccountNameW(
        None,
        account_name,
        sid,
        ctypes.byref(cbSid),
        referenced_domain_name,
        ctypes.byref(cbReferencedDomainName),
        ctypes.byref(peUse),
    )
    if not success:
        last_err = ctypes.get_last_error()
        raise ProfileError(f"Failed to lookup account (error: {last_err})")
    
    # Convert SID to string
    ConvertSidToStringSidW = advapi32.ConvertSidToStringSidW
    ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    ConvertSidToStringSidW.restype = ctypes.c_int
    
    sid_string_ptr = ctypes.c_wchar_p()
    if not ConvertSidToStringSidW(sid, ctypes.byref(sid_string_ptr)):
        last_err = ctypes.get_last_error()
        raise ProfileError(f"Failed to convert SID to string (error: {last_err})")
    
    sid_string = sid_string_ptr.value
    
    # Free the allocated string
    kernel32.LocalFree(sid_string_ptr)
    
    return sid_string


def _profile_path_from_registry(sid: str) -> Optional[str]:
    if SYSTEM != "Windows":
        return None
    
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
        ) as key:
            try:
                with winreg.OpenKey(key, sid) as user_key:
                    profile_image_path, _ = winreg.QueryValueEx(user_key, "ProfileImagePath")
                    return profile_image_path
            except FileNotFoundError:
                return None
    except Exception:
        return None


def create_or_get_profile_path(username: str, domain: str = "") -> str:
    if SYSTEM != "Windows":
        raise ProfileError("Only available on Windows")
    
    if not is_admin():
        raise ProfileError("Administrador necessário para registrar perfil")
    
    sid = _lookup_sid(username, domain)
    
    # Define CreateProfile from userenv.dll
    userenv = ctypes.windll.userenv
    CreateProfile = userenv.CreateProfile
    CreateProfile.restype = ctypes.c_long
    CreateProfile.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
    
    buffer_size = 260
    profile_path = ctypes.create_unicode_buffer(buffer_size)
    
    # Call CreateProfile
    hr = CreateProfile(sid, username, profile_path, buffer_size)
    
    # Check HRESULT
    hr_masked = hr & 0xFFFFFFFF
    if hr_masked == 0x00000000:  # S_OK
        return profile_path.value
    elif hr_masked == 0x800700B7:  # ERROR_ALREADY_EXISTS (0xB7 = 183)
        path = _profile_path_from_registry(sid)
        if path:
            return path
        raise ProfileError("Perfil já existe mas caminho não encontrado no registro")
    elif hr_masked == 0x80070005:  # E_ACCESSDENIED
        raise ProfileError("Permissão negada — execute como Administrador")
    else:
        raise ProfileError(f"Erro ao criar perfil (HRESULT: 0x{hr_masked:08X})")
