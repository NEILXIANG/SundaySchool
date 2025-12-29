# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.datastruct import Tree


datas = []
binaries = []
hiddenimports = []
extra_collect = []


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes")


# Optional: bundle InsightFace model(s) into the packaged artifact for offline teacher deployment.
# Enable via env:
#   SUNDAY_PHOTOS_BUNDLE_INSIGHTFACE_MODELS=1
# Optional overrides:
#   SUNDAY_PHOTOS_INSIGHTFACE_HOME=/path/to/.insightface
#   SUNDAY_PHOTOS_INSIGHTFACE_MODEL=buffalo_l
if _truthy(os.environ.get("SUNDAY_PHOTOS_BUNDLE_INSIGHTFACE_MODELS", "")):
    model_name = (os.environ.get("SUNDAY_PHOTOS_INSIGHTFACE_MODEL") or "").strip() or "buffalo_l"
    model_home = (os.environ.get("SUNDAY_PHOTOS_INSIGHTFACE_HOME") or "").strip() or os.path.expanduser("~/.insightface")
    src_model_dir = os.path.join(model_home, "models", model_name)
    if not os.path.isdir(src_model_dir):
        raise SystemExit(
            "❌ 未找到 InsightFace 模型目录，无法打包离线模型：\n"
            f"- expected: {src_model_dir}\n"
            "你可以先运行一次开发版以下载模型，或设置 SUNDAY_PHOTOS_INSIGHTFACE_HOME 指向已有模型目录。"
        )
    # Bundle only the selected model directory to control size.
    # IMPORTANT: Tree is a build target and must be passed to COLLECT (not Analysis.datas).
    extra_collect.append(Tree(src_model_dir, prefix=f"insightface_home/models/{model_name}"))

# 收集 core（主逻辑）与相关依赖的数据文件。
# 注：在某些开发环境里 face_recognition_models 可能未安装；此时允许继续打包，
# 以便生成基本可执行文件并通过“产物存在性/权限/文档”等验收检查。
for pkg in ("core", "face_recognition_models", "insightface"):
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
    *extra_collect,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SundayPhotoOrganizer",
)
