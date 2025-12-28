#!/usr/bin/env python3
"""
控制台版本打包脚本
将项目打包为纯控制台可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """主打包函数"""
    print("🚀 开始打包控制台版本...")
    
    # 检查必要文件
    required_files = ['console_launcher.py', 'src', 'config.json']
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ 缺少必要文件: {file}")
            return False
    
    print("✅ 所有必要文件检查通过")
    
    # 清理之前的构建
    print("🧹 清理之前的构建文件...")
    dirs_to_clean = ['build_console', 'dist_console']
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  删除: {dir_name}")
    
    print("✅ 清理完成")
    
    # 创建输出目录
    dist_dir = Path('dist_console')
    dist_dir.mkdir(exist_ok=True)
    
    # 运行PyInstaller
    print("📦 开始打包控制台应用程序...")
    try:
        cmd = [
            'pyinstaller',
            '--onefile',                     # 创建单文件可执行程序
            '--console',                     # 控制台应用
            '--noconfirm',                   # 覆盖输出目录
            '--clean',                       # 清理临时文件
            '--name=SundayPhotoOrganizer',   # 可执行文件名
            '--distpath=dist_console',       # 输出目录
            '--workpath=build_console',      # 工作目录
            '--specpath=.',                 # spec文件位置
            '--add-data=src:src',            # 添加源代码目录
            '--add-data=config.json:.',      # 添加配置文件
            '--hidden-import=face_recognition',
            '--hidden-import=PIL',
            '--hidden-import=PIL.Image',
            '--hidden-import=numpy',
            '--hidden-import=tqdm',
            '--hidden-import=dlib',
            '--hidden-import=cv2',
            '--hidden-import=scipy',
            'console_launcher.py'
        ]
        
        print("执行命令:", ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller打包成功")
        else:
            print("❌ PyInstaller打包失败")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程中出错: {e}")
        return False
    
    # 检查输出文件
    executable_path = dist_dir / 'SundayPhotoOrganizer'
    if executable_path.exists():
        print(f"✅ 可执行文件创建成功: {executable_path}")
        
        # 检查文件大小
        size_mb = executable_path.stat().st_size / (1024 * 1024)
        print(f"📦 文件大小: {size_mb:.1f} MB")
        
        # 创建发布目录
        release_dir = Path('release_console')
        release_dir.mkdir(exist_ok=True)
        
        # 复制到发布目录
        release_executable = release_dir / 'SundayPhotoOrganizer'
        if release_executable.exists():
            release_executable.unlink()
        shutil.copy2(executable_path, release_executable)
        
        # 设置执行权限
        os.chmod(release_executable, 0o755)
        
        print(f"✅ 可执行文件已复制到: {release_executable}")
        
        # 创建简化使用说明
        create_console_guide()
        
        print("🎉 控制台版本打包完成！")
        print(f"📦 可执行文件: {release_executable}")
        print(f"📖 使用说明: {release_dir}/使用说明.txt")
        return True
    else:
        print("❌ 可执行文件创建失败")
        return False

def create_console_guide():
    """创建控制台版本使用说明"""
    guide_content = """主日学照片整理工具 - 控制台版本使用说明

🚀 超级简单使用方法：

1. 双击运行 "SundayPhotoOrganizer" 文件
2. 等待程序自动处理
3. 完成！

📁 文件夹位置：
程序会在可执行文件同目录创建这些文件夹：
- input/student_photos（学生照片：学生参考照）
- input/class_photos（课堂照片）
- output（整理结果）
- logs（日志文件）

📸 照片准备：
1. 学生照片：放入 input/student_photos 文件夹
    放法（唯一方式）：input/student_photos/学生名/ 里放照片（文件名随意）
2. 课堂照片：放入 input/class_photos 文件夹
   可以是任何 .jpg 或 .png 文件

💡 使用技巧：
- 第一次运行时，如果找不到照片，请按照提示添加照片
- 后续运行时，只需添加新的课堂照片即可
- 程序会自动打开整理结果文件夹

❓ 常见问题：
Q: 程序运行很快就结束了？
A: 可能是没有找到照片，请检查文件夹位置和照片命名

Q: 识别不准确？
A: 增加每个学生的参考照片数量

Q: 程序无法启动？
A: 确保在 macOS 系统上运行，并允许程序运行权限

---
版本：1.0.0
更新日期：2025-12-21
"""
    
    guide_path = Path('release_console/使用说明.txt')
    guide_path.write_text(guide_content, encoding='utf-8')
    print(f"✅ 使用说明已创建: {guide_path}")

def create_simple_launcher():
    """创建简单的启动脚本（可选）"""
    launcher_content = """#!/bin/bash
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
"""
    
    launcher_path = Path('release_console/启动工具.sh')
    launcher_path.write_text(launcher_content, encoding='utf-8')
    os.chmod(launcher_path, 0o755)
    print(f"✅ 启动脚本已创建: {launcher_path}")

    # Windows launcher (.bat)
    launcher_bat = """@echo off
setlocal

REM Sunday School Photo Organizer - Windows Launcher
REM Keeps the window open so teachers can read messages.

chcp 65001 >nul

set "DIR=%~dp0"
cd /d "%DIR%"

set "EXE=%DIR%SundayPhotoOrganizer.exe"
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
echo.
echo Press any key to exit...
pause >nul
"""

    launcher_bat_path = Path('release_console/Launch_SundayPhotoOrganizer.bat')
    launcher_bat_path.write_text(launcher_bat, encoding='utf-8')
    print(f"✅ Windows 启动脚本已创建: {launcher_bat_path}")

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎊 控制台版本打包成功！")
        print("📂 release_console 文件夹中包含：")
        print("   - SundayPhotoOrganizer（可执行文件）")
        print("   - 使用说明.txt（使用说明）")
        print()
        print("🚀 老师使用步骤：")
        print("1. 将 release_console/ 整个文件夹发给老师（放哪都可以）")
        print("2. 双击运行")
        print("3. 按照提示添加照片")
        print("4. 等待自动完成")
    else:
        print("\n❌ 控制台版本打包失败，请检查错误信息")
        sys.exit(1)
    
    # 额外创建启动脚本
    create_simple_launcher()