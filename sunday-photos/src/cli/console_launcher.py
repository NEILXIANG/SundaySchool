#!/usr/bin/env python3
"""Sunday School Photo Organizer - Console Edition (Packaged Entry)

面向老师的设计目标：最少操作、最少疑惑。

Behavior overview:
- First run: prepare the work folders (input/output/logs) under a teacher-friendly "Work folder".
    - Usually: next to the executable (portable)
    - If not writable: automatically fall back to Desktop (or Home) and print the actual path
- Next runs: organize photos; open output/ when finished

Note:
- The program may move photos under class_photos/ into YYYY-MM-DD/ subfolders (normal; used for incremental processing)
"""

import sys
import os
import argparse
from pathlib import Path
import json
import time
import logging
from datetime import datetime
import platform
import threading
from contextlib import contextmanager
import subprocess
import re
import shutil
import unicodedata
import importlib
import logging
import tempfile
import atexit
import io


def _early_setup_matplotlib_env() -> None:
    """Best-effort: configure Matplotlib *before* any third-party import.

    In multiprocessing spawn, the child process imports __main__ (this file) first.
    If any dependency imports Matplotlib during that phase, multiple workers may try
    to build the font cache concurrently, which can look like a hang.

    We set:
    - MPLBACKEND=Agg (non-GUI, safe for packaged console)
    - MPLCONFIGDIR=<work_dir>/logs/.mplconfig/pid_<pid> (per-process, avoids contention)
      Falling back to a temp directory if work_dir is unknown.
    """

    try:
        os.environ.setdefault("MPLBACKEND", "Agg")

        if os.environ.get("MPLCONFIGDIR", "").strip():
            return

        work_dir = os.environ.get("SUNDAY_PHOTOS_WORK_DIR", "").strip()
        if work_dir:
            base = Path(work_dir) / "logs" / ".mplconfig"
        else:
            base = Path(tempfile.gettempdir()) / "SundayPhotoOrganizer" / "mplconfig"

        cfg_dir = base / f"pid_{os.getpid()}"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(cfg_dir)
    except Exception:
        return


_early_setup_matplotlib_env()

# Ensure project root (containing the src/ package) is importable.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import LOG_FORMAT, UNKNOWN_PHOTOS_DIR
from src.core.platform_paths import get_default_work_root_dir, get_program_dir
from src.core.utils import is_supported_nonempty_image_path


def _try_get_teacher_helper():
    """Best-effort import for friendly teacher-facing error messages."""
    try:
        from src.ui.teacher_helper import TeacherHelper
        return TeacherHelper()
    except Exception:
        return None

class ConsolePhotoOrganizer:
    def __init__(self):
        self._program_dir = get_program_dir()
        self.app_directory = get_default_work_root_dir()
        self.setup_complete = False
        self.teacher_helper = _try_get_teacher_helper()
        self.logger = logging.getLogger(__name__)
        self._hud_width = 56
        self._term_width = 80

        # Console output cleanup:
        # - If two divider lines are printed with only blank lines between,
        #   keep only one to reduce visual noise.
        self._last_emitted_was_divider = False
        self._only_blank_since_divider = False

        # Teacher-friendly: print the "notices" (formerly scattered TIP lines) only once.
        self._notices_printed = False

        # Teacher-friendly pacing: optionally add a tiny pause after *critical* lines
        # so they are easier to perceive when the console scrolls quickly.
        self._ui_pause_ms = self._get_env_int("SUNDAY_PHOTOS_UI_PAUSE_MS", default=0)
        self._ui_pause_ms = max(0, min(int(self._ui_pause_ms), 1000))
        self._ui_pause_last_ts = 0.0

        # Fit divider width to current terminal to reduce line-wrapping artifacts.
        try:
            cols = shutil.get_terminal_size(fallback=(80, 20)).columns
            self._term_width = max(40, cols)
            # Keep messages reasonably narrow to reduce wrapping; dividers use terminal width.
            self._hud_width = min(self._hud_width, max(20, cols - 2))
        except Exception:
            pass

        # Packaged console app: always write a UTF-8 log file under work folder.
        # Do NOT add extra console logging here to keep teacher-facing output stable.
        self._setup_matplotlib_runtime_cache()
        self._acquire_single_instance_lock()
        self._ensure_file_logging()
        self._log_startup_diagnostics()

        # Teacher console palette (techy + minimal): cyan primary + state colors + gray for background details.
        # Keep this mapping stable so VS Code/debug/.app output looks consistent.
        self._label_color_map: dict[str, str] = {
            # Primary / navigation
            "SYS": "36",
            "BOOT": "36",
            "STEP": "36",
            "RUN": "36",
            "MODE": "36",
            "PATH": "36",
            "HUD": "36",
            "GO": "36",
            "AI": "36",
            "SCAN": "36",
            "ORG": "36",
            # State
            "OK": "32",
            "DONE": "32",
            "WARN": "33",
            "NEXT": "34",
            "FAIL": "31",
            # Background / diagnostics
            "DIAG": "90",
            "FULL": "90",
            "UI": "90",
            "TIP": "90",
        }

    def _default_color_for_label(self, label: str) -> str | None:
        try:
            label_norm = (label or "").strip().upper()
            if not label_norm:
                return None
            return self._label_color_map.get(label_norm)
        except Exception:
            return None

    def _get_env_int(self, name: str, *, default: int = 0) -> int:
        try:
            raw = os.environ.get(name, "")
            if raw is None:
                return int(default)
            raw = str(raw).strip()
            if raw == "":
                return int(default)
            return int(float(raw))
        except Exception:
            return int(default)

    def _teacher_mode_enabled(self) -> bool:
        try:
            return os.environ.get("SUNDAY_PHOTOS_TEACHER_MODE", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "y",
                "on",
            )
        except Exception:
            return False

    def _ui_pause_enabled(self) -> bool:
        if self._ui_pause_ms <= 0:
            return False
        if not self._teacher_mode_enabled():
            return False
        try:
            return bool(getattr(sys.stdout, "isatty", lambda: False)())
        except Exception:
            return False

    def _maybe_ui_pause(self) -> None:
        """Best-effort tiny pause to improve perception of critical messages.

        Rules:
        - Only when teacher mode + interactive TTY.
        - Default disabled unless SUNDAY_PHOTOS_UI_PAUSE_MS > 0.
        - Avoid stacking pauses back-to-back.
        """

        if not self._ui_pause_enabled():
            return

        now = time.monotonic()
        # If we just paused very recently, skip to avoid slowing down too much.
        if (now - float(self._ui_pause_last_ts)) < 0.25:
            return

        try:
            time.sleep(float(self._ui_pause_ms) / 1000.0)
            self._ui_pause_last_ts = time.monotonic()
        except Exception:
            return

    def _should_enforce_single_instance(self) -> bool:
        """Return True if we should prevent multiple instances.

        Rationale:
        - Teachers often double-click twice when startup is slow.
        - Multiple concurrent runs can open multiple terminals and duplicate work.
        """
        try:
            if os.environ.get("SUNDAY_PHOTOS_DISABLE_SINGLE_INSTANCE", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "y",
                "on",
            ):
                return False
        except Exception:
            pass

        # Default: enforce only in packaged (frozen) builds.
        try:
            if bool(getattr(sys, "frozen", False)):
                return True
        except Exception:
            pass

        # Allow manual opt-in for dev runs.
        return os.environ.get("SUNDAY_PHOTOS_ENFORCE_SINGLE_INSTANCE", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )

    def _acquire_single_instance_lock(self) -> None:
        """Best-effort single-instance lock (cross-platform).

        Uses an advisory file lock under work_dir/logs/run.lock.
        If lock is held, print a short teacher-friendly message and exit with code 2.
        """
        if not self._should_enforce_single_instance():
            return

        try:
            lock_dir = self.app_directory / "logs"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_path = lock_dir / "run.lock"

            # Keep the file handle open for the lifetime of the process.
            f = open(lock_path, "a+", encoding="utf-8")

            locked = False
            if os.name == "posix":
                try:
                    import fcntl  # type: ignore

                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except Exception:
                    locked = False
            else:
                # Windows best-effort
                try:
                    import msvcrt  # type: ignore

                    # Lock the first byte.
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                except Exception:
                    locked = False

            if not locked:
                try:
                    # Keep message short and actionable.
                    print("⚠️ 程序已在运行，请查看已打开的终端窗口（不要重复双击）。")
                    print("如果你确定没有在运行：请等待 10 秒后再试，或重启电脑后再运行。")
                except Exception:
                    pass
                raise SystemExit(2)

            # Record basic info for support.
            try:
                f.seek(0)
                f.truncate()
                f.write(
                    json.dumps(
                        {
                            "pid": os.getpid(),
                            "started_at": datetime.now().isoformat(timespec="seconds"),
                            "argv": sys.argv,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                f.flush()
            except Exception:
                pass

            self._instance_lock_handle = f

            def _release() -> None:
                try:
                    if os.name == "posix":
                        import fcntl  # type: ignore

                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    else:
                        import msvcrt  # type: ignore

                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
                try:
                    f.close()
                except Exception:
                    pass

            atexit.register(_release)
        except SystemExit:
            raise
        except Exception:
            # Must never block teacher usage.
            return

    def _setup_matplotlib_runtime_cache(self) -> None:
        """Best-effort: make Matplotlib cache location deterministic and writable.

        Some third-party deps may import matplotlib (directly or indirectly).
        In multiprocessing spawn, multiple workers can simultaneously build the font cache,
        causing heavy CPU/disk churn and noisy output.

        We pin MPLCONFIGDIR to a folder under work_dir/logs/ so it is writable and shared.
        """

        try:
            # Do not override if user explicitly set it.
            if os.environ.get("MPLCONFIGDIR", "").strip():
                return

            mpl_dir = self.app_directory / "logs" / ".mplconfig"
            mpl_dir.mkdir(parents=True, exist_ok=True)
            os.environ["MPLCONFIGDIR"] = str(mpl_dir)

            # Prefer non-GUI backend for packaged console runs.
            os.environ.setdefault("MPLBACKEND", "Agg")
        except Exception:
            return

    def _log_startup_diagnostics(self) -> None:
        """Write startup diagnostics to log file (never to console by default).

        This helps debug issues that only happen in packaged/teacher builds,
        such as runaway multiprocessing spawn (process explosion).
        """

        try:
            import socket
            import multiprocessing as mp

            pid = os.getpid()
            try:
                ppid = os.getppid()
            except Exception:
                ppid = -1

            stdout_isatty = bool(getattr(sys.stdout, "isatty", lambda: False)())
            stderr_isatty = bool(getattr(sys.stderr, "isatty", lambda: False)())
            stdin_isatty = bool(getattr(sys.stdin, "isatty", lambda: False)())

            proc_name = ""
            try:
                proc_name = mp.current_process().name
            except Exception:
                proc_name = ""

            parent_proc = None
            try:
                parent_proc = getattr(mp, "parent_process", lambda: None)()
            except Exception:
                parent_proc = None

            self.logger.info("[STARTUP] ===== SundayPhotoOrganizer startup =====")
            self.logger.info(
                "[STARTUP] pid=%s ppid=%s host=%s user=%s",
                pid,
                ppid,
                socket.gethostname(),
                os.environ.get("USER") or os.environ.get("USERNAME") or "",
            )
            self.logger.info(
                "[STARTUP] platform=%s python=%s frozen=%s sys.executable=%s",
                sys.platform,
                sys.version.replace("\n", " "),
                bool(getattr(sys, "frozen", False)),
                sys.executable,
            )
            self.logger.info("[STARTUP] cwd=%s", os.getcwd())
            self.logger.info("[STARTUP] argv=%s", sys.argv)
            self.logger.info("[STARTUP] program_dir=%s work_dir=%s", self._program_dir, self.app_directory)
            self.logger.info(
                "[STARTUP] isatty(stdin=%s stdout=%s stderr=%s) TERM=%s",
                stdin_isatty,
                stdout_isatty,
                stderr_isatty,
                os.environ.get("TERM", ""),
            )
            self.logger.info(
                "[STARTUP] mp.current_process=%s mp.parent_process=%s",
                proc_name,
                getattr(parent_proc, "name", None) if parent_proc is not None else None,
            )

            # Key env vars that affect runtime behavior.
            keys = [
                "SUNDAY_PHOTOS_WORK_DIR",
                "SUNDAY_PHOTOS_NO_PARALLEL",
                "SUNDAY_PHOTOS_PARALLEL",
                "SUNDAY_PHOTOS_PARALLEL_MIN_PHOTOS",
                "SUNDAY_PHOTOS_FACE_BACKEND",
                "SUNDAY_PHOTOS_PRINT_DIAG",
                "SUNDAY_PHOTOS_DIAG_ENV",
                "SUNDAY_PHOTOS_NO_ANIMATION",
                "SUNDAY_PHOTOS_FORCE_ANIMATION",
            ]
            env_snapshot = {k: os.environ.get(k, "") for k in keys}
            self.logger.info("[STARTUP] env=%s", env_snapshot)
        except Exception:
            # Diagnostics must never block teacher usage.
            return

    def _ensure_file_logging(self) -> None:
        """Best-effort configure root logger to write logs/xxx.log.

        Keep it file-only to avoid changing console output and tests.
        """
        try:
            log_dir = self.app_directory / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            root_logger = logging.getLogger()
            # Ensure INFO logs reach the file handler (without touching console output).
            if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
                root_logger.setLevel(logging.INFO)

            # Avoid adding duplicate file handlers.
            for handler in root_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    return

            log_file = log_dir / f"photo_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            root_logger.addHandler(file_handler)
        except Exception:
            # Logging must never block teacher usage.
            return

    def _diag_enabled(self) -> bool:
        return os.environ.get("SUNDAY_PHOTOS_PRINT_DIAG", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        )

    def _normalize_engine_name(self, raw: str) -> str:
        v = (raw or "").strip().lower()
        if v in ("insightface", "insight", "arcface"):
            return "insightface"
        if v in ("dlib", "face_recognition", "facerecognition"):
            return "dlib"
        return "insightface"

    def _try_pkg_version(self, dist_name: str) -> str:
        try:
            # Prefer stdlib importlib.metadata when available.
            try:
                from importlib import metadata as md  # type: ignore
            except Exception:  # pragma: no cover
                md = None  # type: ignore
            if md is not None:
                return str(md.version(dist_name))
        except Exception:
            pass
        return "(unknown)"

    def _print_runtime_diagnostics(self, *, config_file: Path | None = None, config_loader=None) -> None:
        if not self._diag_enabled():
            return

        try:
            frozen = bool(getattr(sys, "frozen", False))
        except Exception:
            frozen = False

        env_engine = os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", "").strip()
        resolved_engine = self._normalize_engine_name(env_engine)
        cfg_engine = ""
        try:
            if config_loader is not None and hasattr(config_loader, "get_face_backend_engine"):
                cfg_engine = str(config_loader.get_face_backend_engine()).strip()
        except Exception:
            cfg_engine = ""

        # Keep output compact and searchable.
        self._print_divider()
        self._print_hud("DIAG", "Runtime diagnostics (SUNDAY_PHOTOS_PRINT_DIAG=1)")
        self._print_hud("DIAG", f"frozen={1 if frozen else 0} python={sys.version.split()[0]}")
        self._print_hud("DIAG", f"sys.executable={sys.executable}")
        self._print_hud("DIAG", f"program_dir={self._program_dir}")
        self._print_hud("DIAG", f"work_dir={self.app_directory}")
        if config_file is not None:
            self._print_hud("DIAG", f"config_file={config_file}")
        self._print_hud(
            "DIAG",
            f"face_backend env='{env_engine or '-'}' config='{cfg_engine or '-'}' resolved='{resolved_engine}'",
        )
        self._print_hud(
            "DIAG",
            "versions: "
            + ", ".join(
                [
                    f"insightface={self._try_pkg_version('insightface')}",
                    f"onnxruntime={self._try_pkg_version('onnxruntime')}",
                    f"opencv-python-headless={self._try_pkg_version('opencv-python-headless')}",
                    f"Pillow={self._try_pkg_version('Pillow')}",
                    f"face-recognition={self._try_pkg_version('face-recognition')}",
                    f"dlib={self._try_pkg_version('dlib')}",
                ]
            ),
        )
        self._print_divider()

    def _print_divider(self):
        self._emit_heavy_divider(self._hud_border("rule"))

    def _print_rule(self) -> None:
        """Light divider for sub-sections (keeps heavy dividers for major sections only)."""
        self._emit_line(self._hud_rule())

    def _rel_path(self, path: Path) -> str:
        """Return a short, readable path relative to WORK_DIR when possible."""
        try:
            base = self.app_directory.resolve()
            target = Path(path).resolve()
            rel = target.relative_to(base)
            return str(rel)
        except Exception:
            try:
                return str(path)
            except Exception:
                return ""

    def _emit_full_path_kv(self, key: str, path: Path, *, color: str | None = None) -> None:
        """Emit an un-truncated FULL line suitable for copy/paste."""
        try:
            tag = self._tag("FULL", color)
            self._emit_line(f"{tag} {key}={path}")
        except Exception:
            return

    def _print_notices_once(self) -> None:
        """Print a single, compact notice block (3 items) for teachers."""
        if self._notices_printed:
            return
        self._notices_printed = True

        self._print_hud("TIP", "注意事项（3条）", color="36")
        self._emit_line(self._hud_line("  1) 支持格式：JPG / JPEG / PNG"))
        self._emit_line(self._hud_line("  2) 隐私：照片只在本机处理，不会自动上传网络"))
        self._emit_line(self._hud_line("  3) 运行时请不要关闭窗口；程序不会删除照片，只会复制结果到 output/"))

        # Give a tiny beat so teachers can visually catch this block.
        self._maybe_ui_pause()

    def _emit_line(self, text: str = "") -> None:
        """Emit a line while collapsing repeated divider lines.

        Rules:
        - Never print a blank line immediately after a divider line.
        - If two divider lines appear with nothing but blanks between them, keep only one.
        """
        try:
            line = "" if text is None else str(text)
        except Exception:
            line = ""

        try:
            is_blank = (line.strip() == "")
        except Exception:
            is_blank = False

        if is_blank:
            # Teachers prefer the divider to be immediately followed by meaningful content.
            if self._last_emitted_was_divider:
                self._only_blank_since_divider = True
                return
            print(line)
            return

        if self._is_divider_line(line):
            self._emit_divider(line)
            return

        # Normal, non-blank, non-divider line.
        self._last_emitted_was_divider = False
        self._only_blank_since_divider = False
        print(line)

    def _emit_divider(self, line: str) -> None:
        """Emit a divider line, collapsing duplicates separated only by blanks."""
        try:
            divider = "" if line is None else str(line)
        except Exception:
            divider = ""

        if self._last_emitted_was_divider and self._only_blank_since_divider:
            return

        print(divider)
        self._last_emitted_was_divider = True
        self._only_blank_since_divider = True

    def _emit_heavy_divider(self, line: str) -> None:
        # Backward-compatible alias.
        self._emit_divider(line)

    def _is_divider_line(self, text: str) -> bool:
        """Return True if text looks like a full-width divider line (═/━/= repeated)."""
        try:
            s = self._strip_ansi(str(text)).strip("\r\n")
            if not s:
                return False
            # Must be a single repeated character.
            if len(set(s)) != 1:
                return False
            ch = s[0]
            if ch not in ("═", "━", "="):
                return False
            # Heuristic: avoid collapsing short sequences that might be meaningful.
            return len(s) >= 40
        except Exception:
            return False

    def _divider_width(self) -> int:
        return max(40, int(self._term_width))

    def _divider_line(self, char: str = "━") -> str:
        width = self._divider_width()
        if not self._unicode_enabled():
            char = "="
        return char * width

    def _unicode_enabled(self) -> bool:
        """Best-effort decide whether unicode box drawing is safe."""
        enc = (getattr(sys.stdout, "encoding", "") or "").lower()
        if "utf" in enc:
            return True
        # macOS terminals generally support unicode even if encoding is not exposed.
        if platform.system() == "Darwin":
            return True
        return False

    def _hud_border(self, kind: str) -> str:
        """Return divider line.

        We intentionally avoid box frames (no '|' side borders) to keep output clean.
        """
        # Teacher console uses the double-line style (═) for a more modern HUD look.
        return self._divider_line("═")

    def _hud_line(self, content: str = "") -> str:
        content = (content or "")
        # Keep within width to reduce wrapping; no framed panel.
        return self._truncate_to_display_width(content, self._hud_width)

    _ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

    def _strip_ansi(self, text: str) -> str:
        return self._ANSI_RE.sub("", text or "")

    def _char_display_width(self, ch: str) -> int:
        # Combining marks and control characters occupy zero columns.
        try:
            if not ch or unicodedata.combining(ch):
                return 0
            cat = unicodedata.category(ch)
            if cat.startswith("C"):
                return 0
            # Treat East Asian wide/fullwidth as 2 columns.
            if unicodedata.east_asian_width(ch) in ("W", "F"):
                return 2
        except Exception:
            return 1
        return 1

    def _display_width(self, text: str) -> int:
        s = self._strip_ansi(text)
        return sum(self._char_display_width(ch) for ch in s)

    def _truncate_to_display_width(self, text: str, max_width: int) -> str:
        if max_width <= 0:
            return ""
        if self._display_width(text) <= max_width:
            return text

        # Reserve 1 column for ellipsis.
        target = max(0, max_width - 1)
        out: list[str] = []
        w = 0
        i = 0
        while i < len(text) and w < target:
            if text[i] == "\x1b":
                m = self._ANSI_RE.match(text, i)
                if m:
                    out.append(m.group(0))
                    i = m.end()
                    continue

            ch = text[i]
            cw = self._char_display_width(ch)
            if w + cw > target:
                break
            out.append(ch)
            w += cw
            i += 1

        out.append("…")
        truncated = "".join(out)
        # If ANSI was used, ensure we reset styles to avoid "bleeding".
        if "\x1b[" in truncated and not truncated.endswith("\x1b[0m"):
            truncated += "\x1b[0m"
        return truncated

    def _hud_rule(self) -> str:
        """A horizontal separator line (double-line style)."""
        return self._divider_line("═")

    def _tag(self, label: str, color_code: str | None = None) -> str:
        """Return a short bracketed tag, optionally colored (TTY-only)."""
        # Fixed width tag for a cyber/HUD look.
        label = (label or "").strip().upper()[:5]
        tag = f"[{label:<5}]"  # keep stable width
        if color_code and self._ansi_enabled():
            return f"\033[1;{color_code}m{tag}\033[0m"
        return tag

    def _print_hud(self, label: str, text: str, *, color: str | None = None) -> None:
        effective_color = color
        if effective_color is None:
            effective_color = self._default_color_for_label(label)

        msg = f"{self._tag(label, effective_color)} {text}"
        # For SYS lines, avoid truncating with ellipsis; long paths should be
        # fully visible (terminal can wrap naturally).
        label_norm = (label or "").strip().upper()
        rendered = msg if label_norm == "SYS" else self._hud_line(msg)
        self._emit_line(rendered)

        # If content was truncated with ellipsis, also print the full message.
        # To avoid overwhelming teachers, skip for verbose TIP/UI blocks.
        try:
            label_norm = (label or "").strip().upper()
            if label_norm not in {"TIP", "UI", "FULL"}:
                raw = self._strip_ansi(msg)
                shown = self._strip_ansi(rendered)
                if shown.endswith("…") and shown != raw:
                    # FULL lines are for copy/paste; keep them low-key (gray) to avoid stealing attention.
                    full_tag = self._tag("FULL", self._default_color_for_label("FULL"))
                    self._emit_line(f"{full_tag} {text}")
        except Exception:
            pass

        # Tiny pause after critical teacher-facing lines (opt-in via env).
        try:
            label_norm = (label or "").strip().upper()
            if label_norm in {"WARN", "NEXT", "RUN", "DONE", "BOOT", "FAIL", "OK"}:
                self._maybe_ui_pause()
        except Exception:
            pass

    def _animation_enabled(self) -> bool:
        """Return True if we should render animated console output.

        Notes:
        - Only enable for interactive terminals (TTY). This keeps pytest output stable
          and prevents capturing tools from seeing carriage-return frames.
        - Teachers can disable animations via env var for accessibility.
        """
        if os.environ.get("SUNDAY_PHOTOS_FORCE_ANIMATION", "").strip().lower() in ("1", "true", "yes", "y", "on"):
            return True
        if not getattr(sys.stdout, "isatty", lambda: False)():
            return False
        term = (os.environ.get("TERM", "") or "").strip().lower()
        if term in ("dumb", "unknown"):
            return False
        if os.environ.get("SUNDAY_PHOTOS_NO_ANIMATION", "").strip().lower() in ("1", "true", "yes", "y", "on"):
            return False
        return True

    def _ansi_enabled(self) -> bool:
        if os.environ.get("SUNDAY_PHOTOS_FORCE_COLOR", "").strip().lower() in ("1", "true", "yes", "y", "on"):
            return True
        if not self._animation_enabled():
            return False
        if os.environ.get("NO_COLOR") is not None:
            return False
        return True

    def _style(self, text: str, *, bold: bool = False) -> str:
        if not self._ansi_enabled():
            return text
        if bold:
            return f"\033[1m{text}\033[0m"
        return text

    def _color(self, text: str, code: str) -> str:
        """Wrap text with an ANSI color code if enabled."""
        if not self._ansi_enabled():
            return text
        return f"\033[{code}m{text}\033[0m"

    @contextmanager
    def _spinner(self, label: str):
        """A tiny spinner shown while doing short blocking work (TTY only)."""
        if not self._animation_enabled():
            yield
            return

        # Use larger, more obvious frames for teachers.
        frames = ["◐", "◓", "◑", "◒"]
        stop_event = threading.Event()

        def _run() -> None:
            i = 0
            try:
                while not stop_event.is_set():
                    frame = frames[i % len(frames)]
                    msg = f"{frame} {label}"
                    print(f"\r{self._style(msg, bold=True)}", end="", flush=True)
                    time.sleep(0.08)
                    i += 1
            finally:
                # Clear the line.
                print("\r" + (" " * (len(label) + 4)) + "\r", end="", flush=True)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        try:
            yield
        finally:
            stop_event.set()
            t.join(timeout=0.3)

    def _pulse(self, label: str, seconds: float = 0.6) -> None:
        """Render a short, obvious pulsing '...' animation (TTY only)."""
        if not self._animation_enabled():
            return
        dots = ["·", "··", "···", "····"]
        colors = ["31", "33", "32", "36", "35", "34"]  # red, yellow, green, cyan, magenta, blue
        end_at = time.time() + max(0.0, seconds)
        i = 0
        while time.time() < end_at:
            suffix = dots[i % len(dots)]
            color = colors[i % len(colors)]
            msg = f"● {label} {suffix}"

            if self._ansi_enabled():
                # Use a single style prefix so the whole line (dot + dots) is clearly colored.
                styled = f"\033[1;{color}m{msg}\033[0m"
            else:
                styled = msg

            print(f"\r{styled}", end="", flush=True)
            time.sleep(0.12)
            i += 1
        print("\r" + (" " * (len(label) + 18)) + "\r", end="", flush=True)

    def _print_section(self, title: str):
        self._emit_line("")
        header = f"◆ {title}"
        # Use a single divider line for section headers (teachers prefer less visual noise).
        self._print_divider()
        self._emit_line(self._hud_line(self._style(header, bold=True) if self._ansi_enabled() else header))

    def _print_tip(self, text: str):
        # Tips are intentionally consolidated into a single "注意事项（3条）" block.
        # Keep this method for backward compatibility, but do not spam the console.
        try:
            self.logger.info("[TIP] %s", text)
        except Exception:
            pass

    def _print_ok(self, text: str):
        # Preserve "[OK]" for any downstream expectations.
        self._emit_line(self._hud_line(f"[OK] {text}"))
        self._maybe_ui_pause()

    def _print_warn(self, text: str):
        self._print_hud("WARN", text, color="33")
        self._maybe_ui_pause()

    def _print_next(self, text: str):
        self._print_hud("NEXT", text, color="34")
        self._maybe_ui_pause()
        
    def print_header(self):
        """打印欢迎信息"""
        # Best-effort: make Windows console output UTF-8 friendly.
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # Optional teacher-friendly banner (hard-coded for this distribution).
        # Uses double-line box drawing "═" when unicode is available.
        banner_line = self._divider_line("═")
        self._emit_heavy_divider(banner_line)
        self._print_hud("SYS", "SUNDAY PHOTO ORGANIZER / 主日学照片整理", color="36")
        self._print_hud("ORG", "LECC / 湖东教会", color="36")
        self._print_hud("MODE", "PIPELINE: SCAN -> MATCH -> SORT -> REPORT", color="36")
        # Keep only one banner divider line.

        self._print_divider()
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        # Keep these keywords stable for tests: "SundayPhotoOrganizer Console" and "WORK_DIR=".
        self._print_hud("SYS", "SYSTEM ONLINE: SundayPhotoOrganizer Console", color="36")
        self._print_hud("SYS", f"RUN_ID={run_id}", color="36")
        # Keep it short (avoid ellipsis). Full path is printed once in the summary below.
        try:
            work_dir_short = str(getattr(self.app_directory, "name", "") or "")
            if not work_dir_short:
                work_dir_short = str(self.app_directory)
        except Exception:
            work_dir_short = str(self.app_directory)
        self._print_hud("SYS", f"WORK_DIR={work_dir_short}", color="36")
        self._print_hud("HUD", "PIPELINE: SCAN -> MATCH -> SORT -> REPORT", color="35")
        self._print_hud("UI", "按提示放照片 → 运行 → 自动输出到 output/", color="35")
        # Teacher-friendly: don't require understanding filesystem permissions.
        override = os.environ.get("SUNDAY_PHOTOS_WORK_DIR", "").strip()
        if override:
            self._print_hud("SYS", "已使用自定义工作目录（由环境变量指定）。", color="36")
        elif self.app_directory != self._program_dir:
            self._print_warn("当前程序所在位置无法创建工作文件夹，我已自动改用其它位置继续运行。")

        # Consolidated notices (print only once).
        self._print_notices_once()

        self._emit_line("")
        self._print_hud("BOOT", "QUICK START / 快速启动", color="36")
        students_dir = self.app_directory / "input" / "student_photos"
        classroom_dir = self.app_directory / "input" / "class_photos"
        output_dir = self.app_directory / "output"
        logs_dir = self.app_directory / "logs"

        # Prefer short, relative paths for readability.
        self._print_hud("PATH", f"STUDENTS={self._rel_path(students_dir)}", color="32")
        self._print_hud("PATH", f"CLASSROOM={self._rel_path(classroom_dir)}", color="32")
        self._print_hud("PATH", f"OUTPUT={self._rel_path(output_dir)}", color="32")
        self._print_hud("PATH", f"LOGS={self._rel_path(logs_dir)}", color="32")

        # Print full paths once for copy/paste.
        self._emit_line("")
        self._emit_line(self._hud_line("完整路径（用于复制粘贴；只在这里显示一次）："))
        self._emit_full_path_kv("WORK_DIR", self.app_directory, color="32")
        self._emit_full_path_kv("STUDENTS", students_dir, color="32")
        self._emit_full_path_kv("CLASSROOM", classroom_dir, color="32")
        self._emit_full_path_kv("OUTPUT", output_dir, color="32")
        self._emit_full_path_kv("LOGS", logs_dir, color="32")
        self._print_hud("GO", "把照片放好后，再运行一次即可。", color="32")
        self._print_divider()
    
    def setup_directories(self):
        """自动创建目录结构"""
        self._print_section("准备工作")
        self._print_hud("SYS", "初始化工作区（文件夹/说明文件）", color="36")
        self._pulse("INIT / workspace")
        
        directories = [
            self.app_directory,
            self.app_directory / "input",
            self.app_directory / "input" / "student_photos",
            self.app_directory / "input" / "class_photos",
            self.app_directory / "output",
            self.app_directory / "logs",
        ]
        
        created_count = 0
        with self._spinner("正在整理工作台（创建/检查文件夹）..."):
            for directory in directories:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    created_count += 1
                    # 不逐项刷屏

            if directory.name == "student_photos":
                self._ensure_instruction_file(
                    directory,
                                        """Student reference photos
Put reference photos under ONE folder per student:

    student_photos/Alice/
    student_photos/Bob/

Filenames can be anything.
Up to 5 reference photos per student will be used (if more than 5, the newest 5 by modified time will be used).
"""
                )
            elif directory.name == "class_photos":
                self._ensure_instruction_file(
                    directory,
                                        """Classroom photos
Put classroom/group photos here.

You may optionally organize by date folders, e.g.:
    class_photos/2025-12-21/group_photo.jpg

Supported formats: .jpg / .jpeg / .png
"""
                )
        
        if created_count > 0:
            self._print_ok(f"文件夹已准备好（新建 {created_count} 个）")
        else:
            self._print_ok("文件夹已准备好")
        self._print_rule()
        return True

    def _ensure_instruction_file(self, directory, content):
        """为老师自动生成说明文件"""
        info_file = directory / "说明.txt"
        if not info_file.exists():
            info_file.write_text(content, encoding='utf-8')
    
    def _try_open_folder(self, folder_path: Path, description: str = "文件夹") -> bool:
        """尝试打开文件夹（跨平台；静默失败）。"""
        try:
            import subprocess
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(['open', str(folder_path)], check=False)
            elif platform.system() == "Windows":
                try:
                    os.startfile(str(folder_path))  # type: ignore[attr-defined]
                except Exception:
                    subprocess.run(['explorer', str(folder_path)], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', str(folder_path)], check=False)
            
            self.logger.debug(f"成功打开{description}: {folder_path}")
            return True
        except Exception as e:
            self.logger.debug(f"打开{description}失败（非关键）: {e}")
            return False
    
    def check_photos(self):
        """检查照片文件"""
        self._print_section("检查照片")
        self._print_hud("SCAN", "扫描输入目录（参考照/课堂照）", color="36")
        self._pulse("SCAN / input")
        
        student_photos_dir = self.app_directory / "input" / "student_photos"
        class_photos_dir = self.app_directory / "input" / "class_photos"
        
        with self._spinner("正在数一数照片（扫描文件夹）..."):
            # Student reference photos: folder-only layout, so scan recursively
            student_photos = [
                p
                for p in student_photos_dir.rglob("*")
                if is_supported_nonempty_image_path(p)
            ]

            # Classroom photos (allow directly under class_photos or under date subfolders)
            class_photos = [
                p
                for p in class_photos_dir.rglob("*")
                if is_supported_nonempty_image_path(p)
            ]
        
        self._print_hud("STAT", f"students={len(student_photos)} / classroom={len(class_photos)}", color="36")
        
        if len(student_photos) == 0:
            self._print_warn("还没有找到学生参考照。")
            self._print_next("Create one folder per student under the folder below, then put clear face photos inside")
            self._print_hud("PATH", f"STUDENTS={self._rel_path(student_photos_dir)}", color="32")
            self._print_rule()
            return False
        
        if len(class_photos) == 0:
            self._print_warn("还没有找到课堂照片。")
            self._print_next("把需要整理的课堂照片放进下面这个文件夹")
            self._print_hud("PATH", f"CLASSROOM={self._rel_path(class_photos_dir)}", color="32")
            self._print_rule()
            return False

        self._print_ok("照片已就绪，可以开始整理。")
        self._print_rule()
        return True
    
    def create_config_file(self):
        """创建配置文件（如已存在则不覆盖），保证默认设置即可运行。"""
        config_data = {
            "input_dir": str(self.app_directory / "input"),
            "output_dir": str(self.app_directory / "output"),
            "log_dir": str(self.app_directory / "logs"),
            # 与 src/core/config_loader.py 读取口径保持一致（顶层字段）。
            "tolerance": 0.6,
            "min_face_size": 50,
            "face_backend": {
                # 默认后端：InsightFace。打包版默认只保证 InsightFace 可用；dlib/face_recognition 属于可选后端。
                "engine": "insightface"
            },
            "parallel_recognition": {
                "enabled": True,
                "workers": 6,
                "chunk_size": 12,
                "min_photos": 30
            },
            "unknown_face_clustering": {
                "enabled": True,
                "threshold": 0.45,
                "min_cluster_size": 2
            }
        }
        
        config_file = self.app_directory / "config.json"
        if config_file.exists():
            return config_file, False

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        return config_file, True

    def _format_friendly_error(self, e: Exception, context: str = "") -> str:
        if self.teacher_helper is None:
            return f"❌ 处理过程中出现错误: {e}\n📍 {context}" if context else f"❌ 处理过程中出现错误: {e}"
        return self.teacher_helper.get_friendly_error(e, context=context)
    
    def process_photos(self):
        """处理照片"""
        self._print_section("开始整理")
        self._print_hud("AI", "进入整理模式：识别 → 分类 → 输出", color="35")
        # Keep it short and stable; SYS lines are not truncated (they wrap naturally).
        self._print_hud("SYS", "执行中请看进度条；完成后打开 output/。", color="36")
        
        start_time = time.time()
        
        try:
            # 导入处理模块
            with self._spinner("正在唤醒 AI 识别引擎（加载依赖）..."):
                from src.core.main import SimplePhotoOrganizer
                from src.core.config_loader import ConfigLoader

            self._pulse("NEURAL / warmup", seconds=0.8)
            
            # 创建/读取配置文件（存在则不覆盖；老师无需调参）
            with self._spinner("正在准备默认配置（无需你动手）..."):
                config_file, created = self.create_config_file()
            if created:
                self._print_ok("已自动生成默认配置（无需修改）")
            else:
                self._print_hud("SYS", "检测到已有配置，将直接使用。", color="36")

            config_loader = ConfigLoader(str(config_file))

            # Optional: print runtime diagnostics to help confirm backend/deps in packaged builds.
            self._print_runtime_diagnostics(config_file=Path(config_file), config_loader=config_loader)
            
            with self._spinner("正在启动整理流程（初始化系统）..."):
                organizer = SimplePhotoOrganizer(
                    input_dir=str(self.app_directory / "input"),
                    output_dir=str(self.app_directory / "output"),
                    log_dir=str(self.app_directory / "logs"),
                    config_file=str(config_file),
                )

                if not organizer.initialize():
                    raise RuntimeError("系统初始化失败，请检查日志文件")

            self._print_ok("AI 识别引擎已就绪")
            
            tolerance = config_loader.get_tolerance()
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                organizer.face_recognizer.tolerance = tolerance

            min_face_size = config_loader.get_min_face_size()
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                organizer.face_recognizer.min_face_size = min_face_size
            
            self._print_hud("STEP", "1/4 载入参考照：建立识别资料库", color="36")
            self._emit_line(self._hud_rule())
            self._print_hud("STEP", "2/4 分析课堂照：检测人脸 → 匹配姓名 → 分类保存", color="36")
            self._emit_line(self._hud_rule())
            self._print_hud("STEP", "3/4 写入结果：复制照片 + 生成统计报告", color="36")
            self._emit_line(self._hud_rule())
            self._print_hud("STEP", "4/4 打开输出：尝试为你打开 output/", color="36")
            self._emit_line(self._hud_rule())
            self._print_hud("SYS", "提示：进度条在动 = 正常运行；长时间不动可能是在计算。", color="36")

            # Give a short beat after stage overview.
            self._maybe_ui_pause()

            # Clear visual boundary before the heavy pipeline output (tqdm, stats).
            self._emit_line(self._hud_line())
            self._print_hud("RUN", "开始执行识别流水线（请关注进度条）", color="35")
            self._emit_line(self._hud_rule())

            # Divider before the verbose pipeline output.
            self._print_divider()
            
            # 运行完整流程
            success = organizer.run()
            elapsed_time = time.time() - start_time
            
            if not success:
                self._print_section("未完成")
                self._print_warn("整理没有完成。")
                self._print_next(f"先打开日志看看原因：{self.app_directory / 'logs'}")
                self._print_divider()
                return False
            
            report = organizer.last_run_report or {}
            organize_stats = report.get('organize_stats', {})
            pipeline_stats = report.get('pipeline_stats', {})
            self._print_hud("RUN", "收尾：整理结果并生成统计", color="35")
            self._print_ok("整理完成。")
            
            # 显示详细结果
            self.display_results(organize_stats, elapsed_time, pipeline_stats)
            
            # 显示文件位置
            output_dir = self.app_directory / "output"
            self._print_hud("PATH", f"OUTPUT={self._rel_path(output_dir)}", color="32")
            self._print_next("如果看到 unknown_photos/，表示未识别；补 2-3 张更清晰参考照通常有帮助。")
            
            # 自动打开结果文件夹
            self._print_hud("SYS", "我来帮你打开结果文件夹...", color="36")
            if self._try_open_folder(output_dir, "结果文件夹"):
                self._print_ok("已打开结果文件夹。")
            else:
                self._print_warn("我没能自动打开文件夹（不影响结果）。")
                self._print_next("请手动打开这个文件夹查看结果")
                self._emit_line(self._hud_line(f"  {self._rel_path(output_dir)}"))

            # Final tiny beat so the end messages don't get visually lost.
            self._maybe_ui_pause()

            return True
            
        except Exception as e:
            context = ""
            self.logger.exception("控制台启动器主流程失败")
            try:
                context = f"工作目录：{self.app_directory}；日志目录：{self.app_directory / 'logs'}"
            except Exception:
                pass

            self._emit_line("")
            self._print_divider()
            self._emit_line("[错误] 程序遇到问题（不用紧张）")
            self._print_divider()
            self._emit_line(self._format_friendly_error(e, context=context))
            self._emit_line("\n你可以按下面顺序检查：")
            self._emit_line("  1) 确认 student_photos/ 与 class_photos/ 里都放了照片")
            self._emit_line("  2) Reference photos: put them in student_photos/<student_name>/ (folder); filenames can be anything")
            self._emit_line("  3) 识别不准：给该学生补 2-3 张更清晰的正脸参考照")
            self._emit_line(f"  4) 需要求助：把 logs 里最新日志发给同工/技术支持：{self.app_directory / 'logs'}")

            self._maybe_ui_pause()
            return False
    
    def display_results(self, results, elapsed_time, pipeline_stats=None):
        """显示处理结果"""
        pipeline_stats = pipeline_stats or {}
        total_from_pipeline = pipeline_stats.get('total_photos', results.get('total', 0))
        self._print_section("结果小结")
        self._print_hud("TIME", f"用时：{elapsed_time:.1f} 秒", color="36")
        self._print_hud("STAT", f"总照片：{total_from_pipeline} 张", color="36")
        self._print_hud("STAT", f"已分类：{results.get('copied', 0)} 张", color="36")
        self._print_hud("STAT", f"失败：{results.get('failed', 0)} 张", color="36")
        self._print_hud(
            "STAT",
            f"未识别（unknown）：{pipeline_stats.get('unknown_photos', results.get('students', {}).get(UNKNOWN_PHOTOS_DIR, 0))} 张",
            color="36",
        )
        if 'no_face_photos' in pipeline_stats:
            self._print_hud("STAT", f"无人脸（no_face）：{pipeline_stats.get('no_face_photos', 0)} 张", color="36")
        if 'error_photos' in pipeline_stats:
            self._print_hud("STAT", f"出错（error）：{pipeline_stats.get('error_photos', 0)} 张", color="36")
        
        students = results.get('students', {})
        detected_students = pipeline_stats.get('students_detected', list(students.keys()))
        self._print_hud("STAT", f"识别到学生：{len(detected_students)} 人", color="36")
        
        if students:
            print()
            # 对老师来说按学生逐条刷屏可能过长；仅保留总体统计。

        self._print_hud("DONE", "照片已按学生姓名分类保存到 output/。", color="32")
        self._print_rule()
    
    def run_auto(self):
        """自动运行模式"""
        self.print_header()
        
        # 设置文件夹
        if not self.setup_directories():
            return False
        
        # 检查照片
        if not self.check_photos():
            print()
            self._print_next("把照片放到上面提示的位置，然后再运行一次")
            print(f"桌面文件夹：{self.app_directory}")
            return False
        
        # 处理照片
        success = self.process_photos()
        
        if success:
            print()
            self._print_ok("完成。")
        else:
            print()
            self._print_warn("未完成，请按上面的提示检查后重试。")
        
        return success


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="SundayPhotoOrganizer",
        add_help=False,
        description="主日学课堂照片自动整理工具（打包控制台版）",
    )
    parser.add_argument("-h", "--help", action="store_true", help="显示此帮助信息并退出")
    # Hidden: used by CI/smoke tests to validate packaged entry startup.
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    return parser


def _print_console_help() -> None:
    # Keep this concise and stable; stdout only.
    print("主日学课堂照片自动整理工具（打包控制台版）")
    print()
    print("用法:")
    print("  SundayPhotoOrganizer              # 自动运行：检查并整理照片")
    print("  SundayPhotoOrganizer --help       # 显示帮助并退出")
    print()
    print("工作目录（运行后会自动生成这些文件夹）:")
    print("  input/student_photos/   每个学生的参考照（按学生姓名建文件夹）")
    print("  input/class_photos/     当天课堂照片（可直接放照片或按日期子文件夹）")
    print("  output/                 输出：按学生姓名分类后的照片")
    print("  logs/                   日志")
    print()
    print("提示:")
    print("  - 首次运行若程序目录不可写，会自动改用桌面/主目录下的工作文件夹")
    print("  - 如需更多开发者选项，请使用源码版入口：python run.py --help")

def main():
    """主函数"""
    # PyInstaller / frozen app + multiprocessing (spawn) requires freeze_support.
    # Without it, child processes may re-run the main program and quickly exhaust
    # system resources (looks like memory/GPU runaway in the teacher .app).
    try:
        import multiprocessing as mp

        mp.freeze_support()
    except Exception:
        pass

    is_interactive = bool(getattr(sys.stdin, "isatty", lambda: False)()) and bool(
        getattr(sys.stdout, "isatty", lambda: False)()
    )
    try:
        parser = _build_arg_parser()
        args, _unknown = parser.parse_known_args(sys.argv[1:])
        if getattr(args, "help", False):
            _print_console_help()
            return True

        # Smoke mode: initialize and exit quickly (writes startup diagnostics to logs/).
        if getattr(args, "smoke", False):
            _ = ConsolePhotoOrganizer()
            # Ensure file handlers flush before exiting.
            try:
                logging.shutdown()
            except Exception:
                pass
            return True

        organizer = ConsolePhotoOrganizer()
        success = organizer.run_auto()
        
        if not success:
            print()
            print("按回车键退出...")
            if is_interactive:
                input()
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n[停止] 程序已被你中断")
        return False
    except Exception as e:
        print(f"\n[错误] 程序启动失败: {e}")
        print("按回车键退出...")
        if is_interactive:
            input()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)