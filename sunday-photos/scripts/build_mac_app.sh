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

    # 给老师的占位说明：把照片放到正确的 input 子目录
    cat > "$RELEASE_DIR/input/student_photos/把学生参考照放这里.txt" <<'EOF'
请把“学生参考照”放到这个文件夹里（用于识别每位学生）。

建议：每位学生 1~5 张，清晰正脸、光线充足、不要过度美颜。
示例文件名：张三_1.jpg、张三_2.jpg
EOF
    cat > "$RELEASE_DIR/input/class_photos/把课堂照片放这里.txt" <<'EOF'
请把“课堂/活动照片（需要整理的照片）”放到这个文件夹里。

示例文件名：2025-12-25_活动_001.jpg
EOF
    cat > "$RELEASE_DIR/input/student_photos/PUT_STUDENT_PHOTOS_HERE.txt" <<'EOF'
Put student reference photos here (used to recognize each student).

Tip: 1–5 photos per student; clear frontal face works best.
Example: Alice_1.jpg, Alice_2.jpg
EOF
    cat > "$RELEASE_DIR/input/class_photos/PUT_CLASS_PHOTOS_HERE.txt" <<'EOF'
Put class/event photos to be organized here.

Example: 2025-12-25_Event_001.jpg
EOF

    # 复制最新 onefile 可执行文件到发布目录根部：release_console/SundayPhotoOrganizer
    # 兼容旧版本：如果之前是目录结构（release_console/SundayPhotoOrganizer/），这里需要 rm -rf
    rm -rf "$RELEASE_DIR/$APP_NAME"
    cp "dist/$APP_NAME" "$RELEASE_DIR/$APP_NAME"
    chmod +x "$RELEASE_DIR/$APP_NAME" || true

    # 将“老师快速开始”文档复制到发布目录（每次打包都刷新一份）
    # 老师只需要看 release_console/ 里的文件即可
    cp -f "doc/TeacherQuickStart.md" "$RELEASE_DIR/老师快速开始.md" || true
    cp -f "doc/TeacherQuickStart.txt" "$RELEASE_DIR/老师快速开始.txt" || true
    cp -f "doc/TeacherQuickStart_en.md" "$RELEASE_DIR/QuickStart_EN.md" || true
    cp -f "doc/TeacherQuickStart_en.txt" "$RELEASE_DIR/QuickStart_EN.txt" || true

    echo "✅ 发布目录已准备好：$RELEASE_DIR"
    echo "   - 已预创建 input/class_photos、input/student_photos、output、logs"
    echo "   - 可执行文件：$RELEASE_DIR/$APP_NAME"
else
    echo "❌ 打包失败，请检查错误信息。"
fi