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
# 老师模式：核心日志不在控制台刷屏（只写 logs/）。
# 默认关闭控制台动画（spinner/pulse）。某些终端对 \r 支持不佳会导致“刷屏/轮询打印”。
: "${SUNDAY_PHOTOS_UI_PAUSE_MS:=200}"
SUNDAY_PHOTOS_WORK_DIR="$DIR" SUNDAY_PHOTOS_TEACHER_MODE=1 SUNDAY_PHOTOS_NO_ANIMATION=1 SUNDAY_PHOTOS_UI_PAUSE_MS="$SUNDAY_PHOTOS_UI_PAUSE_MS" "$EXECUTABLE" "$@"

echo ""
echo "程序运行完成。按回车键退出..."
if [ -t 0 ]; then
    read
fi
