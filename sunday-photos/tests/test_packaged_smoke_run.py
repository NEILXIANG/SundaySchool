#!/usr/bin/env python3
"""Smoke test: run the packaged console executable.

Why:
- The teacher macOS .app ultimately launches the packaged console binary.
- We want a lightweight check that the packaged entry can start and exit
  successfully (without GUI dependencies).

This test runs:
- release_console/SundayPhotoOrganizer/(SundayPhotoOrganizer|SundayPhotoOrganizer.exe) --help

Policy:
- If release_console/ is missing, skip by default.
- If REQUIRE_PACKAGED_ARTIFACTS=1, missing artifacts should fail (no skip).
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)

RELEASE_DIR = PROJECT_ROOT / "release_console"
EXECUTABLE = RELEASE_DIR / "SundayPhotoOrganizer"


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def _require_packaged_artifacts() -> bool:
    return _truthy_env("REQUIRE_PACKAGED_ARTIFACTS", default="0")


def _skip_if_missing_release_dir() -> bool:
    if RELEASE_DIR.exists():
        return False
    if _require_packaged_artifacts():
        return False
    pytest.skip("未发现 release_console/（未打包），跳过打包运行 smoke test")


def _resolve_console_executable() -> Path:
    """Resolve runnable console executable for both onefile and onedir layouts."""
    candidate = EXECUTABLE
    if candidate.is_file():
        return candidate
    if candidate.is_dir():
        if sys.platform.startswith("win"):
            return candidate / "SundayPhotoOrganizer.exe"
        return candidate / "SundayPhotoOrganizer"
    return candidate


def test_packaged_console_runs_smoke_and_writes_startup_log(tmp_path: Path):
    """Packaged executable should start and write startup diagnostics in smoke mode."""

    _skip_if_missing_release_dir()

    exe = _resolve_console_executable()
    if not exe.exists():
        if _require_packaged_artifacts():
            pytest.fail("未发现 release_console 可执行文件（REQUIRE_PACKAGED_ARTIFACTS=1）")
        pytest.skip("未发现 release_console 可执行文件，跳过")

    if not os.access(exe, os.X_OK):
        pytest.fail(f"打包可执行文件不可执行: {exe}")

    env = dict(os.environ)
    # Isolate any writes and avoid touching repo/release folders.
    env["SUNDAY_PHOTOS_WORK_DIR"] = str(tmp_path)
    # Make the smoke test as stable as possible.
    env.setdefault("SUNDAY_PHOTOS_NO_ANIMATION", "1")
    env.setdefault("SUNDAY_PHOTOS_NO_PARALLEL", "1")

    result = subprocess.run(
        [str(exe), "--smoke"],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"smoke 退出码异常: {result.returncode}\n输出:\n{result.stdout}"

    logs_dir = tmp_path / "logs"
    log_files = sorted(logs_dir.glob("photo_organizer_*.log"))
    assert log_files, f"未生成启动日志文件: {logs_dir}\n输出:\n{result.stdout}"

    latest_log = log_files[-1]
    content = latest_log.read_text(encoding="utf-8", errors="replace")
    if "[STARTUP]" not in content:
        if _require_packaged_artifacts():
            pytest.fail(
                f"启动日志缺少 [STARTUP] 标记（REQUIRE_PACKAGED_ARTIFACTS=1，需为最新打包产物）: {latest_log}\n"
                f"日志内容:\n{content}"
            )
        pytest.skip("release_console 产物可能较旧（未包含启动诊断日志）；重新打包后再运行该测试")
