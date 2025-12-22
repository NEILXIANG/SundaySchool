#!/bin/bash
# 主日学照片整理工具启动脚本

echo "🏫 正在启动主日学照片整理工具..."

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
EXECUTABLE="$DIR/SundayPhotoOrganizer"

# 检查可执行文件是否存在
if [ ! -f "$EXECUTABLE" ]; then
    echo "❌ 找不到可执行文件: $EXECUTABLE"
    read -p "按回车键退出..."
    exit 1
fi

# 运行程序
"$EXECUTABLE"

# 程序结束后等待用户确认
echo ""
echo "程序运行完成。按回车键退出..."
read
