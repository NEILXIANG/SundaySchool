# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all


datas = []
binaries = []
hiddenimports = []

# 收集 core（主逻辑）与 face_recognition_models（依赖模型数据）。
# 注：在某些开发环境里 face_recognition_models 可能未安装；此时允许继续打包，
# 以便生成基本可执行文件并通过“产物存在性/权限/文档”等验收检查。
for pkg in ("core", "face_recognition_models"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        # Best-effort: skip optional package collection.
        pass


a = Analysis(
    ["console_launcher.py"],
    pathex=["src", "."],
    binaries=binaries,
    # 额外打包 src/，确保控制台启动器可加载到完整运行时文件。
    # 注意：不要把 config.json 打进包里（老师端需要在工作目录生成/使用自己的配置，避免携带开发机绝对路径）。
    datas=datas + [("src", "src")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 该 spec 生成 onedir 控制台应用目录：dist/SundayPhotoOrganizer/
# Windows 不支持 .icns；若未安装 Pillow 则无法自动转换，导致打包失败。
# 为保证 CI 稳定：Windows 不设置 icon；其他平台继续使用 app_icon.icns。
icon_files = [] if sys.platform.startswith("win") else ["app_icon.icns"]

# 在提供 .spec 时，PyInstaller 不允许通过 CLI 传入 --target-arch。
# 这里改为通过环境变量 TARGET_ARCH 传入（仅对 macOS 有意义；其他平台保持 None）。
env_target_arch = (os.environ.get("TARGET_ARCH") or "").strip() or None
target_arch_value = env_target_arch if sys.platform == "darwin" else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SundayPhotoOrganizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch_value,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_files,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SundayPhotoOrganizer",
)
