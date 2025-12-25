#!/bin/bash
set -e

# 打包主日学照片整理工具为 macOS 桌面应用
# 使用 PyInstaller 打包

# 确保当前目录为项目根目录
cd "$(dirname "$0")/.."

# 图标文件路径
ICON_PATH="app_icon.icns"

# 可选目标架构：设置环境变量 TARGET_ARCH=universal2 或 arm64 或 x86_64
TARGET_ARCH=${TARGET_ARCH:-}
if [ -n "$TARGET_ARCH" ]; then
    echo "Target arch: $TARGET_ARCH"
fi

# 优先使用工作区根目录的 .venv（测试任务也使用它），其次才用 sunday-photos/venv
PYTHON="$(pwd)/../.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(pwd)/.venv/bin/python"
fi
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(pwd)/venv/bin/python"
fi
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

# 检查 PyInstaller 是否安装（在同一 python 环境中）
if ! "$PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    echo "PyInstaller 未安装（当前 python: $PYTHON）"
    echo "请运行: $PYTHON -m pip install pyinstaller"
    exit 1
fi

# 打包命令（控制台 onefile）：PyInstaller 会先生成 dist/SundayPhotoOrganizer
SPEC_FILE="SundayPhotoOrganizer.spec"

"$PYTHON" -m PyInstaller \
    --clean \
    --noconfirm \
    "$SPEC_FILE"

# 打包完成后，准备发布目录并预创建老师需要的空目录
if [ $? -eq 0 ]; then
    echo "🎉 打包成功！中间产物位于 dist/，已复制到 release_console/ 作为交付目录。"

    RELEASE_DIR="release_console"
    APP_NAME="SundayPhotoOrganizer"

    # 清理旧发布产物（保留说明文件）
    mkdir -p "$RELEASE_DIR"
    mkdir -p "$RELEASE_DIR/input/class_photos"
    mkdir -p "$RELEASE_DIR/input/student_photos"
    mkdir -p "$RELEASE_DIR/output"
    mkdir -p "$RELEASE_DIR/logs"

    # 复制最新 onefile 可执行文件到发布目录根部：release_console/SundayPhotoOrganizer
    # 兼容旧版本：如果之前是目录结构（release_console/SundayPhotoOrganizer/），这里需要 rm -rf
    rm -rf "$RELEASE_DIR/$APP_NAME"
    cp "dist/$APP_NAME" "$RELEASE_DIR/$APP_NAME"
    chmod +x "$RELEASE_DIR/$APP_NAME" || true

    echo "✅ 发布目录已准备好：$RELEASE_DIR"
    echo "   - 已预创建 input/class_photos、input/student_photos、output、logs"
    echo "   - 可执行文件：$RELEASE_DIR/$APP_NAME"
else
    echo "❌ 打包失败，请检查错误信息。"
fi