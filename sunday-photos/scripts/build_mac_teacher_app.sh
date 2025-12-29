#!/bin/bash
set -euo pipefail

# Build a teacher-friendly macOS .app wrapper (with icon) that launches the
# packaged console binary.
#
# Default behavior: open Terminal and show console output (teacher-friendly).
# Optional: set RUN_MODE=silent to run in background without opening Terminal.
#
# Notes:
# - The console launcher is patched to avoid blocking on input() when not
#   running in an interactive TTY (required for silent mode).

cd "$(dirname "$0")/.."

APP_NAME="SundayPhotoOrganizer"
RELEASE_CONSOLE_DIR="release_console"
CONSOLE_DIR="$RELEASE_CONSOLE_DIR/$APP_NAME"
CONSOLE_ENTRY="$CONSOLE_DIR/$APP_NAME"
RELEASE_APP_DIR="release_mac_app"
APP_BUNDLE="$RELEASE_APP_DIR/$APP_NAME.app"
ICON_ICNS="app_icon.icns"
RUN_MODE="${RUN_MODE:-terminal}"

# Bundle InsightFace models into the packaged artifact for offline teacher deployment.
# Default ON for teacher .app build.
BUNDLE_INSIGHTFACE_MODELS="${BUNDLE_INSIGHTFACE_MODELS:-1}"
MODEL_NAME="${SUNDAY_PHOTOS_INSIGHTFACE_MODEL:-buffalo_l}"

if [ ! -f "$ICON_ICNS" ]; then
  echo "❌ 缺少图标文件: $ICON_ICNS"
  exit 1
fi

# If bundling is enabled, ensure the console artifact includes the bundled model directory.
NEED_MODEL_REBUILD=0
if [ "$BUNDLE_INSIGHTFACE_MODELS" = "1" ]; then
  if [ ! -d "$CONSOLE_DIR/insightface_home/models/$MODEL_NAME" ]; then
    NEED_MODEL_REBUILD=1
  fi
fi

# Ensure we have a console app dir to wrap.
if [ "${FORCE_REBUILD_CONSOLE:-}" = "1" ] || [ "$NEED_MODEL_REBUILD" = "1" ] || [ ! -x "$CONSOLE_ENTRY" ]; then
  echo "🔧 构建控制台可执行文件（用于 .app 内部调用）..."
  if [ "$BUNDLE_INSIGHTFACE_MODELS" = "1" ]; then
    echo "📦 将 InsightFace 模型打包进产物（离线可用）: $MODEL_NAME"
    export SUNDAY_PHOTOS_BUNDLE_INSIGHTFACE_MODELS=1
  fi
  bash "scripts/build_mac_app.sh"
else
  echo "✅ 使用已存在的控制台可执行文件: $CONSOLE_ENTRY"
fi

if [ ! -x "$CONSOLE_ENTRY" ]; then
  echo "❌ 未找到可执行文件: $CONSOLE_ENTRY"
  exit 1
fi

# Clean and prepare release dir.
# NOTE: When the teacher .app is launched in Terminal mode, the spawned shell can
# end up with its CWD set to release_mac_app/. On macOS, removing a process's CWD
# directory can fail (sometimes reported as "Permission denied").
#
# To make rebuilds reliable, keep the directory and wipe its contents.
mkdir -p "$RELEASE_APP_DIR"
rm -rf \
  "$RELEASE_APP_DIR"/* \
  "$RELEASE_APP_DIR"/.[!.]* \
  "$RELEASE_APP_DIR"/..?* \
  2>/dev/null || true

# Prepare teacher-facing work folders next to the .app (so teachers can see input/output/logs).
mkdir -p "$RELEASE_APP_DIR/input/class_photos"
mkdir -p "$RELEASE_APP_DIR/input/student_photos"
mkdir -p "$RELEASE_APP_DIR/output"
mkdir -p "$RELEASE_APP_DIR/logs"

# Generate release config.json (minimal): keep parallel enabled and cap workers for stability.
cat > "$RELEASE_APP_DIR/config.json" <<'EOF'
{
  "_comment": "发布包最小配置：仅覆盖并行识别参数；其他均使用程序默认值。",
  "parallel_recognition": {
    "enabled": true,
    "workers": 4,
    "chunk_size": 12,
    "min_photos": 30
  }
}
EOF

cat > "$RELEASE_APP_DIR/input/student_photos/把学生参考照放这里.md" <<'EOF'
请把“学生参考照”放到这个文件夹里（用于识别每位学生）。

建议：每位学生 1~5 张，清晰正脸、光线充足、不要过度美颜。
示例文件名：张三_1.jpg、张三_2.jpg
EOF
cat > "$RELEASE_APP_DIR/input/class_photos/把课堂照片放这里.md" <<'EOF'
请把“课堂/活动照片（需要整理的照片）”放到这个文件夹里。

示例文件名：2025-12-25_活动_001.jpg
EOF
cat > "$RELEASE_APP_DIR/input/student_photos/PUT_STUDENT_PHOTOS_HERE.md" <<'EOF'
Put student reference photos here (used to recognize each student).

Tip: 1–5 photos per student; clear frontal face works best.
Example: Alice_1.jpg, Alice_2.jpg
EOF
cat > "$RELEASE_APP_DIR/input/class_photos/PUT_CLASS_PHOTOS_HERE.md" <<'EOF'
Put class/event photos to be organized here.

Example: 2025-12-25_Event_001.jpg
EOF

# Remove legacy .txt placeholders (always keep only .md).
rm -f \
  "$RELEASE_APP_DIR/input/student_photos/把学生参考照放这里.txt" \
  "$RELEASE_APP_DIR/input/class_photos/把课堂照片放这里.txt" \
  "$RELEASE_APP_DIR/input/student_photos/PUT_STUDENT_PHOTOS_HERE.txt" \
  "$RELEASE_APP_DIR/input/class_photos/PUT_CLASS_PHOTOS_HERE.txt" \
  || true

# Build AppleScript app.
# It will locate its own Resources folder and run the bundled binary.
OSASCRIPT_FILE="$(mktemp -t sunday_photos_applet).applescript"

if [ "$RUN_MODE" = "silent" ]; then
  cat > "$OSASCRIPT_FILE" <<'APPLESCRIPT'
on run
  set appBundlePath to POSIX path of (path to me)
  set parentDir to do shell script "/usr/bin/dirname " & quoted form of appBundlePath
  set resourcesDir to appBundlePath & "Contents/Resources"
  set exePath to resourcesDir & "/SundayPhotoOrganizer/SundayPhotoOrganizer"
  set mplConfigDir to parentDir & "/logs/mplconfig"
  set cmd to "cd " & quoted form of parentDir & " && /bin/mkdir -p " & quoted form of mplConfigDir & " && /usr/bin/nohup /usr/bin/env " & ¬
    "SUNDAY_PHOTOS_WORK_DIR=" & quoted form of parentDir & " " & ¬
    "MPLBACKEND=Agg " & ¬
    "MPLCONFIGDIR=" & quoted form of mplConfigDir & " " & ¬
    "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 " & ¬
    "SUNDAY_PHOTOS_PARALLEL_STRATEGY=threads " & ¬
    quoted form of exePath & " >/dev/null 2>&1 &"
  do shell script cmd
end run
APPLESCRIPT
else
  cat > "$OSASCRIPT_FILE" <<'APPLESCRIPT'
on run
  set appBundlePath to POSIX path of (path to me)
  set parentDir to do shell script "/usr/bin/dirname " & quoted form of appBundlePath
  set resourcesDir to appBundlePath & "Contents/Resources"
  set exePath to resourcesDir & "/SundayPhotoOrganizer/SundayPhotoOrganizer"
  set mplConfigDir to parentDir & "/logs/mplconfig"
  set cmd to "cd " & quoted form of parentDir & " && /bin/mkdir -p " & quoted form of mplConfigDir & " && /usr/bin/env " & ¬
    "SUNDAY_PHOTOS_WORK_DIR=" & quoted form of parentDir & " " & ¬
    "MPLBACKEND=Agg " & ¬
    "MPLCONFIGDIR=" & quoted form of mplConfigDir & " " & ¬
    "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 " & ¬
    "SUNDAY_PHOTOS_PARALLEL_STRATEGY=threads " & ¬
    quoted form of exePath

  tell application "Terminal"
    activate
    do script cmd
  end tell
end run
APPLESCRIPT
fi

echo "📦 生成 .app: $APP_BUNDLE"
osacompile -o "$APP_BUNDLE" "$OSASCRIPT_FILE"
rm -f "$OSASCRIPT_FILE" || true

# Copy onedir bundle into app bundle resources.
mkdir -p "$APP_BUNDLE/Contents/Resources"
rm -rf "$APP_BUNDLE/Contents/Resources/$APP_NAME"
cp -R "$CONSOLE_DIR" "$APP_BUNDLE/Contents/Resources/$APP_NAME"
chmod +x "$APP_BUNDLE/Contents/Resources/$APP_NAME/$APP_NAME" || true

# Replace default applet icon.
# AppleScript apps use applet.icns by default.
cp -f "$ICON_ICNS" "$APP_BUNDLE/Contents/Resources/applet.icns"

# Copy teacher docs next to the .app for convenience.
cp -f "doc/TeacherQuickStart.md" "$RELEASE_APP_DIR/老师快速开始.md" || true
cp -f "doc/TeacherQuickStart_en.md" "$RELEASE_APP_DIR/QuickStart_EN.md" || true

# Teacher docs: always keep only .md (remove any .txt if present).
rm -f \
  "$RELEASE_APP_DIR/老师快速开始.txt" \
  "$RELEASE_APP_DIR/QuickStart_EN.txt" \
  || true

cat > "$RELEASE_APP_DIR/使用说明_启动方式.md" <<'EOF'
# macOS 启动方式（老师版 .app）

1) 双击 `SundayPhotoOrganizer.app` 启动。
2) 默认会自动打开“终端 Terminal”窗口显示运行进度（控制台信息）。

可选（高级/静默模式）：
- 重新生成 app 时设置 `RUN_MODE=silent`，可让程序后台运行、不打开终端。
- 静默模式下请查看工作目录 `logs/` 里的日志。

如果 macOS 提示“无法打开/来自未知开发者”：
- 系统设置 → 隐私与安全性 → 找到被拦截的 app → 仍要打开。
EOF

# Remove legacy .txt usage file.
rm -f "$RELEASE_APP_DIR/使用说明_启动方式.txt" || true

echo "✅ 完成：$APP_BUNDLE"
echo "   发布目录：$RELEASE_APP_DIR"
