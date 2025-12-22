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
ARCH_FLAG=()
if [ -n "$TARGET_ARCH" ]; then
    ARCH_FLAG=(--target-arch "$TARGET_ARCH")
    echo "Target arch: $TARGET_ARCH"
fi

# 检查 PyInstaller 是否安装
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller 未安装，请运行以下命令安装:"
    echo "pip install pyinstaller"
    exit 1
fi

# 打包命令
pyinstaller \
    --clean \
    --console \
    --noupx \
    --paths src \
    --collect-all core \
    --collect-all face_recognition_models \
    "${ARCH_FLAG[@]}" \
    --icon="$ICON_PATH" \
    src/cli/run.py

# 打包完成后，准备发布目录并预创建老师需要的空目录
if [ $? -eq 0 ]; then
    echo "🎉 打包成功！可执行文件位于 dist/ 目录下。"

    RELEASE_DIR="release_console"
    APP_NAME="SundayPhotoOrganizer"

    # 清理旧发布产物（保留说明文件）
    mkdir -p "$RELEASE_DIR"
    mkdir -p "$RELEASE_DIR/input/class_photos"
    mkdir -p "$RELEASE_DIR/input/student_photos"
    mkdir -p "$RELEASE_DIR/output"
    mkdir -p "$RELEASE_DIR/logs"

    # 复制最新 onedir 目录（含所有依赖）
    rm -rf "$RELEASE_DIR/$APP_NAME"
    mkdir -p "$RELEASE_DIR/$APP_NAME"
    cp -R dist/run/ "$RELEASE_DIR/$APP_NAME/"

    echo "✅ 发布目录已准备好：$RELEASE_DIR"
    echo "   - 已预创建 input/class_photos、input/student_photos、output、logs"
    echo "   - 可执行目录：$RELEASE_DIR/$APP_NAME (内含 run 可执行文件)"
else
    echo "❌ 打包失败，请检查错误信息。"
fi