from __future__ import annotations

import os
import sys
from pathlib import Path


def get_desktop_dir() -> Path:
    """Return the user's Desktop directory in a cross-platform way.

    - Windows: use SHGetKnownFolderPath(FOLDERID_Desktop) when possible.
    - macOS/Linux: prefer ~/Desktop if it exists, else fall back to home.

    Always returns a Path that exists or can be created (we don't create it here).
    """

    if sys.platform == "win32":
        desktop = _windows_known_folder_desktop()
        if desktop is not None:
            return desktop

        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            return Path(user_profile) / "Desktop"

        return Path.home() / "Desktop"

    desktop = Path.home() / "Desktop"
    return desktop if desktop.exists() else Path.home()


def _windows_known_folder_desktop() -> Path | None:
    try:
        import ctypes
        from ctypes import wintypes

        # FOLDERID_Desktop = {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8),
            ]

        def _guid_from_string(guid_str: str) -> GUID:
            import uuid

            u = uuid.UUID(guid_str)
            data4 = (wintypes.BYTE * 8).from_buffer_copy(u.bytes[8:])
            return GUID(u.fields[0], u.fields[1], u.fields[2], data4)

        folder_id = _guid_from_string("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")

        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT

        path_ptr = ctypes.c_wchar_p()
        hr = SHGetKnownFolderPath(ctypes.byref(folder_id), 0, 0, ctypes.byref(path_ptr))
        if hr != 0 or not path_ptr.value:
            return None

        desktop = Path(path_ptr.value)
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return desktop

    except Exception:
        return None
