#!/usr/bin/env python3
"""
主日学课堂照片自动整理工具 - 简化版
运行入口
"""

import os
import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
 
from core.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_TOLERANCE
from core.main import SimplePhotoOrganizer

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    
    # 检查依赖包
    required_packages = ['face_recognition', 'PIL', 'numpy', 'tqdm']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少依赖包:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n💡 请运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        return False
    
    print("✅ 环境检查通过")
    return True

def show_help():
    """显示帮助信息"""
    help_text = f"""
🏫 主日学课堂照片自动整理工具 (简化版)

📋 使用方法:
    1. 将学生参考照片放入 {DEFAULT_INPUT_DIR}/student_photos/ 目录
    2. 照片文件名格式：姓名 或 姓名_序号（如：张三.jpg 或 张三_1.jpg）
    3. 将待整理课堂照片放入 {DEFAULT_INPUT_DIR}/class_photos/ 目录，可按日期子目录存放（如 2024-12-21/照片.jpg）
    4. 运行此程序

📁 目录结构示例:
   input/
   ├── student_photos/
   │   ├── 张三.jpg
   │   ├── 张三_2.jpg
   │   ├── 李四.jpg
   │   └── 王五_1.jpg
   └── class_photos/
       ├── 2024-12-21/
       │   ├── 班级活动.jpg
       │   └── ...
       └── 2024-12-28/
           └── ...

⚙️ 命令行选项:
    --input-dir      输入数据目录 (默认: {DEFAULT_INPUT_DIR})
    --classroom-dir  输入数据目录兼容参数（已废弃，隐藏）
    --output-dir     输出目录 (默认: {DEFAULT_OUTPUT_DIR})
    --tolerance      人脸识别阈值 (0-1, 默认: {DEFAULT_TOLERANCE})
    --help           显示此帮助信息

🚀 运行程序:
   python run.py

🆘 遇到问题?
   - 检查照片格式是否支持 (jpg, png等)
   - 确保参考照片清晰且包含完整人脸
   - 调整识别阈值 (0.4-0.8之间)
"""
    print(help_text)

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="主日学课堂照片自动整理工具 - 简化版",
        add_help=False
    )
    
    parser.add_argument(
        "--input-dir", 
        default=DEFAULT_INPUT_DIR,
        help="输入数据目录 (默认: input)"
    )

    # 兼容旧参数名称
    parser.add_argument(
        "--classroom-dir", 
        dest="classroom_dir",
        help=argparse.SUPPRESS
    )
    
    parser.add_argument(
        "--output-dir", 
        default=DEFAULT_OUTPUT_DIR,
        help="输出目录 (默认: output)"
    )
    
    parser.add_argument(
        "--tolerance", 
        type=float, 
        default=DEFAULT_TOLERANCE,
        help="人脸识别阈值 (0-1, 默认: 0.6)"
    )
    
    parser.add_argument(
        "--help",
        action="store_true",
        help="显示帮助信息"
    )
    
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="检查运行环境"
    )
    
    args = parser.parse_args()
    input_dir = args.input_dir or getattr(args, "classroom_dir", None)
    if not input_dir and getattr(args, "classroom_dir", None):
        input_dir = args.classroom_dir
    
    # 显示帮助
    if args.help:
        show_help()
        return
    
    # 检查环境
    if args.check_env:
        check_environment()
        return
    
    # 启动画面
    print("\n" + "="*60)
    print("🏫 主日学课堂照片自动整理工具 (简化版)")
    print("="*60)
    
    # 环境检查
    if not check_environment():
        print("\n❌ 环境检查失败，请解决上述问题后重试")
        sys.exit(1)
    
    # 导入主模块并运行
    try:
        print("\n🚀 启动照片整理程序...")
        
        # 创建整理器实例
        organizer = SimplePhotoOrganizer(
            input_dir=input_dir,
            classroom_dir=getattr(args, "classroom_dir", None),
            output_dir=args.output_dir
        )
        
        # 初始化系统（这会初始化face_recognizer）
        if not organizer.initialize():
            print("\n❌ 系统初始化失败")
            sys.exit(1)
            
        # 设置人脸识别阈值
        if hasattr(organizer, 'face_recognizer'):
            organizer.face_recognizer.tolerance = args.tolerance
        
        # 运行整理流程
        success = organizer.run()
        
        if success:
            print("\n🎉 程序执行完成！")
        else:
            print("\n❌ 程序执行失败，请查看日志了解详情")
            sys.exit(1)
            
    except ImportError as e:
        print(f"\n❌ 导入模块失败: {e}")
        print("请确保所有依赖包都已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print("请查看详细日志了解问题原因")
        sys.exit(1)

if __name__ == "__main__":
    main()