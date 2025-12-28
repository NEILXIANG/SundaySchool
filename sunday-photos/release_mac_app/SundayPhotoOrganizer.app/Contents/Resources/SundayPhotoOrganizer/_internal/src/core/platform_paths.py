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


def get_program_dir() -> Path:
    """Return the directory containing the running program.

    - PyInstaller / frozen app: use sys.executable
    - Normal python execution: prefer argv[0]
    - Fallback: current working directory
    """

    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            return Path.cwd()

    try:
        if sys.argv and sys.argv[0]:
            return Path(sys.argv[0]).resolve().parent
    except Exception:
        pass

    return Path.cwd()


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            return False
        probe = path / ".__write_probe__"
        probe.write_bytes(b"x")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def get_default_work_root_dir() -> Path:
    """Pick a teacher-friendly *root* directory for work files.

    Requirement: work folders should live alongside the executable when possible,
    i.e. create ./input, ./output, ./logs next to the app.

    Priority:
    1) Explicit override via env var SUNDAY_PHOTOS_WORK_DIR (root dir)
    2) Next to the executable/script (portable, "wherever you put the app")
    3) Desktop fallback
    4) Home fallback
    """

    override = os.environ.get("SUNDAY_PHOTOS_WORK_DIR", "").strip()
    if override:
        return Path(override).expanduser()

    candidates = [
        get_program_dir(),
        get_desktop_dir(),
        Path.home(),
    ]

    for candidate in candidates:
        if candidate.exists() and _is_writable_dir(candidate):
            return candidate

    # Best-effort: return the first one.
    return candidates[0]


def get_default_work_dir(app_folder_name: str = "SundaySchoolPhotoOrganizer") -> Path:
    """Backward-compatible helper: return a dedicated subfolder under the chosen root."""

    return get_default_work_root_dir() / app_folder_name


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
