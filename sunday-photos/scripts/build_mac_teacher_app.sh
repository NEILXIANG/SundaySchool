#!/bin/bash
set -euo pipefail

# Build a teacher-friendly macOS .app wrapper (with icon) that launches the
# packaged console binary.
#
# Important: this build intentionally avoids AppleScript/AppleEvents so the app
# can be launched by double-clicking without controlling other apps.

cd "$(dirname "$0")/.."

APP_NAME="SundayPhotoOrganizer"
RELEASE_CONSOLE_DIR="release_console"
CONSOLE_DIR="$RELEASE_CONSOLE_DIR/$APP_NAME"
CONSOLE_ENTRY="$CONSOLE_DIR/$APP_NAME"
RELEASE_APP_DIR="release_mac_app"
APP_BUNDLE="$RELEASE_APP_DIR/$APP_NAME.app"
ICON_ICNS="app_icon.icns"

# Best-effort: keep app_icon.icns fresh (macOS directory mtime is not reliable
# when modifying existing PNGs under app_icon.iconset).
if [ -d "app_icon.iconset" ] && command -v iconutil >/dev/null 2>&1; then
  echo "🎨 生成图标: $ICON_ICNS"
  iconutil -c icns "app_icon.iconset" -o "$ICON_ICNS"
fi

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

# Build a standard macOS .app bundle with a launcher script (no AppleScript / no AppleEvents).
echo "📦 生成 .app（标准 launcher，无 AppleEvent）: $APP_BUNDLE"

mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Minimal Info.plist (avoid the long list of AppleScript permission prompts).
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>
  <string>app_icon</string>
  <key>CFBundleIdentifier</key>
  <string>org.sundayschool.$APP_NAME</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.4.0</string>
  <key>CFBundleVersion</key>
  <string>0.4.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.13</string>
</dict>
</plist>
EOF

# Icon
cp -f "$ICON_ICNS" "$APP_BUNDLE/Contents/Resources/app_icon.icns"

# Copy onedir bundle into app bundle resources.
rm -rf "$APP_BUNDLE/Contents/Resources/$APP_NAME"
cp -R "$CONSOLE_DIR" "$APP_BUNDLE/Contents/Resources/$APP_NAME"
chmod +x "$APP_BUNDLE/Contents/Resources/$APP_NAME/$APP_NAME" || true

# Launcher (opens Terminal.app and runs the bundled binary with visible console).
cat > "$APP_BUNDLE/Contents/MacOS/$APP_NAME" <<'SH'
#!/bin/bash
set -euo pipefail

# Resolve paths
THIS_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTENTS_DIR="$(cd "$THIS_DIR/.." && pwd)"
APP_BUNDLE_DIR="$(cd "$CONTENTS_DIR/.." && pwd)"
WORK_DIR="$(cd "$APP_BUNDLE_DIR/.." && pwd)"  # release_mac_app/
RESOURCES_DIR="$CONTENTS_DIR/Resources"
APP_NAME="SundayPhotoOrganizer"
EXE="$RESOURCES_DIR/$APP_NAME/$APP_NAME"
MPLCONFIG_DIR="$WORK_DIR/logs/mplconfig"

mkdir -p "$MPLCONFIG_DIR" "$WORK_DIR/output" "$WORK_DIR/logs" || true

# Best-effort: remove quarantine attributes so double-click works after unzip.
/usr/bin/xattr -cr "$APP_BUNDLE_DIR" "$RESOURCES_DIR/$APP_NAME" 2>/dev/null || true

# Best-effort: avoid duplicate runs (common teacher double-click).
if /usr/bin/pgrep -f "$EXE" >/dev/null 2>&1; then
  /usr/bin/osascript -e 'display dialog "程序已在运行，请查看已打开的终端窗口（不要重复双击）。" buttons {"好的"} default button 1' >/dev/null 2>&1 || true
  exit 0
fi

if [ ! -x "$EXE" ]; then
  /usr/bin/osascript -e 'display dialog "错误：找不到可执行文件，请检查安装是否完整。" buttons {"好的"} default button 1' >/dev/null 2>&1 || true
  /usr/bin/open "$WORK_DIR/logs" >/dev/null 2>&1 || true
  exit 1
fi

# Build command to run in Terminal
CMD="cd $(printf %q "$WORK_DIR") && /bin/mkdir -p $(printf %q "$MPLCONFIG_DIR") && /usr/bin/clear && /usr/bin/env SUNDAY_PHOTOS_TEACHER_MODE=1 SUNDAY_PHOTOS_UI_PAUSE_MS=200 SUNDAY_PHOTOS_WORK_DIR=$(printf %q "$WORK_DIR") MPLBACKEND=Agg MPLCONFIGDIR=$(printf %q "$MPLCONFIG_DIR") OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 SUNDAY_PHOTOS_PARALLEL_STRATEGY=threads $(printf %q "$EXE")"

# Open Terminal.app and run the command
/usr/bin/osascript -e "tell application \"Terminal\"" -e "activate" -e "do script \"$CMD\"" -e "end tell" >/dev/null 2>&1

exit 0
SH
chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

# Best-effort: refresh LaunchServices/Finder icon cache so the icon shows in Finder.
touch "$APP_BUNDLE" "$APP_BUNDLE/Contents/Info.plist" "$APP_BUNDLE/Contents/Resources/app_icon.icns" 2>/dev/null || true
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [ -x "$LSREGISTER" ]; then
  "$LSREGISTER" -f "$APP_BUNDLE" >/dev/null 2>&1 || true
fi

# Generate minimal README for teacher release (replaces verbose doc copies).
cat > "$RELEASE_APP_DIR/README.md" <<'EOF'
# SundayPhotoOrganizer（macOS 版）

## 快速开始

### 首次使用（网络下载/AirDrop 接收后）

**重要：** 从网络下载或 AirDrop 接收后，请先执行：

1. 双击 `首次运行前清理.command`（清除 macOS 隔离属性）
2. 双击 `SundayPhotoOrganizer.app` 启动

**或** 右键点击 `SundayPhotoOrganizer.app` → 选择"打开"（绕过 Gatekeeper）

### 日常使用

1. 双击 `SundayPhotoOrganizer.app`
2. 学生参考照放 `input/student_photos/<学生名>/`
3. 课堂照片放 `input/class_photos/`
4. 完成后自动打开 `output/` 文件夹

## 日志位置

- `logs/teacher_app_console.log` - 启动器控制台输出（排障首选）
- `logs/` - 程序运行日志

## 详细文档

- [完整教师指南](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/TeacherGuide.md)
- [配置参考手册](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/CONFIG_REFERENCE.md)
- [常见问题](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/FAQ.md)
EOF

cat > "$RELEASE_APP_DIR/README_EN.md" <<'EOF'
# SundayPhotoOrganizer (macOS)

## Quick Start

### First Use (After Network Download/AirDrop)

**Important:** If downloaded from the internet or received via AirDrop:

1. Double-click `首次运行前清理.command` (clears macOS quarantine)
2. Double-click `SundayPhotoOrganizer.app` to launch

**Or** Right-click `SundayPhotoOrganizer.app` → Open (bypasses Gatekeeper)

### Daily Use

1. Double-click `SundayPhotoOrganizer.app`
2. Student photos → `input/student_photos/<student_name>/`
3. Class photos → `input/class_photos/`
4. Auto-opens `output/` folder when done

## Logs

- `logs/teacher_app_console.log` - Launcher console output (check first)
- `logs/` - Application logs

## Full Documentation

- [Teacher Guide](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/TeacherGuide_en.md)
- [Config Reference](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/CONFIG_REFERENCE_en.md)
- [FAQ](https://github.com/NEILXIANG/SundaySchool/blob/main/sunday-photos/doc/FAQ_en.md)
EOF

# Clean up legacy teacher doc copies and .txt files.
rm -f \
  "$RELEASE_APP_DIR/老师快速开始.md" \
  "$RELEASE_APP_DIR/QuickStart_EN.md" \
  "$RELEASE_APP_DIR/老师使用指南.md" \
  "$RELEASE_APP_DIR/TeacherGuide_EN.md" \
  "$RELEASE_APP_DIR/配置参考手册.md" \
  "$RELEASE_APP_DIR/CONFIG_REFERENCE_EN.md" \
  "$RELEASE_APP_DIR/使用说明_启动方式.md" \
  "$RELEASE_APP_DIR/使用说明_启动方式.txt" \
  "$RELEASE_APP_DIR/老师快速开始.txt" \
  "$RELEASE_APP_DIR/QuickStart_EN.txt" \
  || true

# Generate external cleanup script (for first-time network download).
cat > "$RELEASE_APP_DIR/首次运行前清理.command" <<'CLEANUP'
#!/bin/bash
# 首次从网络下载后运行此脚本，清除 macOS 隔离属性
set -euo pipefail
cd "$(dirname "$0")"

APP="SundayPhotoOrganizer.app"

# 1) Clear quarantine attributes (most common cause)
/usr/bin/xattr -cr . 2>/dev/null || true

# 2) Best-effort: ad-hoc re-sign after unzipping/downloading.
# Some macOS versions show "已损坏" when Gatekeeper thinks the signature is invalid.
if [ -d "$APP" ] && [ -x /usr/bin/codesign ]; then
  /usr/bin/codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
fi

# 3) Best-effort: register the app with spctl (may help on some systems)
if [ -d "$APP" ] && [ -x /usr/sbin/spctl ]; then
  /usr/sbin/spctl --add --label "SundayPhotoOrganizer" "$APP" >/dev/null 2>&1 || true
fi

echo "✅ 已执行清理/修复，现在可以双击 SundayPhotoOrganizer.app 启动"
sleep 1
# 自动关闭当前 Terminal 窗口
/usr/bin/osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 || true
CLEANUP
chmod +x "$RELEASE_APP_DIR/首次运行前清理.command"

echo "✅ 完成：$APP_BUNDLE"
echo "   发布目录：$RELEASE_APP_DIR"
