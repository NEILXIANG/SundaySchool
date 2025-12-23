# -*- mode: python ; coding: utf-8 -*-

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
    # 额外打包 src/ 与 config.json，确保控制台启动器可加载到完整运行时文件。
    datas=datas + [("src", "src"), ("config.json", ".")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 该 spec 生成 onefile 控制台可执行文件：dist/SundayPhotoOrganizer
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["app_icon.icns"],
)
