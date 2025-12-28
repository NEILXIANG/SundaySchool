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

# 打包命令（控制台 onedir）：PyInstaller 会生成 dist/SundayPhotoOrganizer/
SPEC_FILE="SundayPhotoOrganizer.spec"
APP_NAME="SundayPhotoOrganizer"

# 使用项目内缓存目录，避免全局 pyinstaller cache 权限/缺失导致的构建失败。
# 注意：PyInstaller 使用 PYINSTALLER_CONFIG_DIR 来决定缓存目录（包含 bincache）。
# 这里强制使用项目内目录，避免用户 shell 环境里残留的 PYINSTALLER_CONFIG_DIR 干扰构建。
PYINSTALLER_CONFIG_DIR_LOCAL="$(pwd)/build/pyinstaller-cache"
mkdir -p "$PYINSTALLER_CONFIG_DIR_LOCAL"

if [ "${SKIP_PYINSTALLER:-}" = "1" ]; then
    echo "ℹ️ SKIP_PYINSTALLER=1：跳过 PyInstaller 构建，复用 dist/$APP_NAME/。"
    if [ ! -x "dist/$APP_NAME/$APP_NAME" ]; then
        echo "❌ 未找到 dist/$APP_NAME/$APP_NAME（需要先成功构建一次）。"
        exit 1
    fi
else
    PYINSTALLER_CONFIG_DIR="$PYINSTALLER_CONFIG_DIR_LOCAL" "$PYTHON" -m PyInstaller \
        --clean \
        --noconfirm \
        "$SPEC_FILE"
fi

# 打包完成后，准备发布目录并预创建老师需要的空目录
if [ $? -eq 0 ]; then
    echo "🎉 打包成功！中间产物位于 dist/，已复制到 release_console/ 作为交付目录。"

    RELEASE_DIR="release_console"

    # 清理旧发布产物（保留说明文件）
    mkdir -p "$RELEASE_DIR"
    mkdir -p "$RELEASE_DIR/input/class_photos"
    mkdir -p "$RELEASE_DIR/input/student_photos"
    mkdir -p "$RELEASE_DIR/output"
    mkdir -p "$RELEASE_DIR/logs"

    # 删除可能残留的 config.json（它可能包含开发机绝对路径）。
    # 打包版会在首次运行时自动生成正确的配置。
    rm -f "$RELEASE_DIR/config.json" || true

    # 给老师的占位说明：把照片放到正确的 input 子目录
    cat > "$RELEASE_DIR/input/student_photos/把学生参考照放这里.md" <<'EOF'
请把“学生参考照”放到这个文件夹里（用于识别每位学生）。

建议：每位学生 1~5 张，清晰正脸、光线充足、不要过度美颜。
示例文件名：张三_1.jpg、张三_2.jpg
EOF
    cat > "$RELEASE_DIR/input/class_photos/把课堂照片放这里.md" <<'EOF'
请把“课堂/活动照片（需要整理的照片）”放到这个文件夹里。

示例文件名：2025-12-25_活动_001.jpg
EOF
    cat > "$RELEASE_DIR/input/student_photos/PUT_STUDENT_PHOTOS_HERE.md" <<'EOF'
Put student reference photos here (used to recognize each student).

Tip: 1–5 photos per student; clear frontal face works best.
Example: Alice_1.jpg, Alice_2.jpg
EOF
    cat > "$RELEASE_DIR/input/class_photos/PUT_CLASS_PHOTOS_HERE.md" <<'EOF'
Put class/event photos to be organized here.

Example: 2025-12-25_Event_001.jpg
EOF

    # Remove legacy .txt placeholders (always keep only .md).
    rm -f \
        "$RELEASE_DIR/input/student_photos/把学生参考照放这里.txt" \
        "$RELEASE_DIR/input/class_photos/把课堂照片放这里.txt" \
        "$RELEASE_DIR/input/student_photos/PUT_STUDENT_PHOTOS_HERE.txt" \
        "$RELEASE_DIR/input/class_photos/PUT_CLASS_PHOTOS_HERE.txt" \
        || true

    # 复制最新 onedir 应用目录到发布目录：release_console/SundayPhotoOrganizer/
    # 兼容旧版本：如果之前是单文件（release_console/SundayPhotoOrganizer），这里需要 rm -rf
    rm -rf "$RELEASE_DIR/$APP_NAME"
    cp -R "dist/$APP_NAME" "$RELEASE_DIR/$APP_NAME"
    chmod +x "$RELEASE_DIR/$APP_NAME/$APP_NAME" || true

    # 将“老师快速开始”文档复制到发布目录（每次打包都刷新一份）
    # 老师只需要看 release_console/ 里的文件即可
    cp -f "doc/TeacherQuickStart.md" "$RELEASE_DIR/老师快速开始.md" || true
    cp -f "doc/TeacherQuickStart_en.md" "$RELEASE_DIR/QuickStart_EN.md" || true

    # 老师文档只保留 .md：无论内容是否相同，都不分发 .txt。
    rm -f \
        "$RELEASE_DIR/老师快速开始.txt" \
        "$RELEASE_DIR/QuickStart_EN.txt" \
        || true

        # 生成启动脚本与简要说明（release_console/ 作为“完全可分发产物”）。
        cat > "$RELEASE_DIR/启动工具.sh" <<'EOF'
#!/bin/bash
set -e

echo "🏫 正在启动主日学照片整理工具..."

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

EXECUTABLE_ONEFILE="$DIR/SundayPhotoOrganizer"
EXECUTABLE_ONEDIR="$DIR/SundayPhotoOrganizer/SundayPhotoOrganizer"

if [ -f "$EXECUTABLE_ONEFILE" ] && [ -x "$EXECUTABLE_ONEFILE" ]; then
    EXECUTABLE="$EXECUTABLE_ONEFILE"
elif [ -x "$EXECUTABLE_ONEDIR" ]; then
    EXECUTABLE="$EXECUTABLE_ONEDIR"
else
    echo "❌ 找不到可执行文件："
    echo "- $EXECUTABLE_ONEFILE"
    echo "- $EXECUTABLE_ONEDIR"
    if [ -t 0 ]; then
        read -p "按回车键退出..."
    fi
    exit 1
fi

# 强制工作目录为解压根目录：确保 input/output/logs 都在老师能看到的位置。
SUNDAY_PHOTOS_WORK_DIR="$DIR" "$EXECUTABLE" "$@"

echo ""
echo "程序运行完成。按回车键退出..."
if [ -t 0 ]; then
    read
fi
EOF
        chmod +x "$RELEASE_DIR/启动工具.sh" || true

        cat > "$RELEASE_DIR/Launch_SundayPhotoOrganizer.bat" <<'EOF'
@echo off
setlocal

REM Sunday School Photo Organizer - Windows Launcher
REM Keeps the console window open so teachers can read messages.

chcp 65001 >nul

set "DIR=%~dp0"
cd /d "%DIR%"

REM Force work dir to the extracted folder root (so input/output/logs live next to this .bat)
set "SUNDAY_PHOTOS_WORK_DIR=%DIR%"

set "EXE=%DIR%SundayPhotoOrganizer\SundayPhotoOrganizer.exe"
if not exist "%EXE%" set "EXE=%DIR%SundayPhotoOrganizer.exe"
if not exist "%EXE%" set "EXE=%DIR%SundayPhotoOrganizer"

if not exist "%EXE%" (
    echo [ERROR] Cannot find SundayPhotoOrganizer executable in:
    echo   %DIR%
    echo.
    echo Expected file:
    echo   SundayPhotoOrganizer.exe
    echo.
    pause
    exit /b 1
)

"%EXE%"

REM If the program succeeded, open output folder for convenience.
if %errorlevel% EQU 0 (
    if exist "%DIR%output\" (
        start "" "%DIR%output"
    )
)

echo.
echo Press any key to exit...
pause >nul
EOF

                    cat > "$RELEASE_DIR/使用说明.md" <<'EOF'
# 使用说明（老师版）

## 使用方法
- 双击运行：
    - macOS：双击 `启动工具.sh`（控制台版）。如果你拿到的是 `.app` 版本，则双击 `SundayPhotoOrganizer.app`。
    - Windows：双击 `Launch_SundayPhotoOrganizer.bat`。
- 放照片：
    - 学生照片（参考照）：`input/student_photos/<学生名>/...`
    - 课堂照片（待整理）：`input/class_photos/`（可按日期建子目录）
- 再运行一次：整理完成后会自动打开 `output/`。

## 文件夹位置
- 工作目录：默认在“启动器所在目录”（例如解压后的文件夹根目录）。
    - 如果目录不可写，程序可能回退到桌面/主目录，并在控制台打印 `Work folder:` 实际路径。
- 输入：`input/`（学生照片/课堂照片）
- 输出：`output/`
- 日志：`logs/`

## 常见问题
- 运行后没有结果：确认 `input/class_photos/` 里有课堂照片。
- 识别不准：尽量提供清晰正脸的学生照片（每人 1–5 张）。

更详细说明请看：`老师快速开始.md`
EOF

          cat > "$RELEASE_DIR/USAGE_EN.md" <<'EOF'
# Teacher usage (short)

1) Put student reference photos into: `input/student_photos/` (one folder per student)
2) Put class photos into: `input/class_photos/`
3) Run:
    - macOS: double-click `SundayPhotoOrganizer.app` (recommended) or `启动工具.sh`
    - Windows: double-click `Launch_SundayPhotoOrganizer.bat`
4) Results: `output/`   Logs: `logs/`

See `QuickStart_EN.md` for details.
EOF

        # Remove legacy .txt usage files (always keep only .md).
        rm -f \
            "$RELEASE_DIR/使用说明.txt" \
            "$RELEASE_DIR/USAGE_EN.txt" \
            || true

    echo "✅ 发布目录已准备好：$RELEASE_DIR"
    echo "   - 已预创建 input/class_photos、input/student_photos、output、logs"
    echo "   - 可执行文件：$RELEASE_DIR/$APP_NAME"
else
    echo "❌ 打包失败，请检查错误信息。"
fi