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
