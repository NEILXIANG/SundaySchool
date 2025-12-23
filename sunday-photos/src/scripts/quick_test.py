#!/usr/bin/env python3
"""快速测试脚本"""
import sys
import os
from pathlib import Path

# 设置路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

print("=== 快速功能测试 ===")

# 测试1: 导入模块
try:
    from config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR
    print("✓ config导入成功")
except Exception as e:
    print(f"✗ config导入失败: {e}")
    sys.exit(1)

# 测试2: 配置加载器
try:
    from config_loader import ConfigLoader
    config = ConfigLoader()
    input_dir = config.get_input_dir()
    print(f"✓ 配置加载成功: input_dir={input_dir}")
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    sys.exit(1)

# 测试3: 学生管理器
try:
    from student_manager import StudentManager
    sm = StudentManager(input_dir)
    students = sm.get_student_names()
    print(f"✓ 学生管理器正常: 找到{len(students)}个学生")
except Exception as e:
    print(f"✗ 学生管理器失败: {e}")
    sys.exit(1)

# 测试4: 人脸识别器
try:
    from face_recognizer import FaceRecognizer
    fr = FaceRecognizer(sm)
    print("✓ 人脸识别器初始化成功")
except Exception as e:
    print(f"✗ 人脸识别器失败: {e}")
    sys.exit(1)

# 测试5: 文件整理器
try:
    from file_organizer import FileOrganizer
    fo = FileOrganizer()
    print("✓ 文件整理器初始化成功")
except Exception as e:
    print(f"✗ 文件整理器失败: {e}")
    sys.exit(1)

# 测试6: 工具函数
try:
    from utils import setup_logger
    logger = setup_logger("test")
    print("✓ 日志设置成功")
except Exception as e:
    print(f"✗ 日志设置失败: {e}")
    sys.exit(1)

# 测试7: 教师辅助功能
try:
    from ui.teacher_helper import TeacherHelper
    helper = TeacherHelper()
    msg = helper.get_friendly_error(FileNotFoundError("测试文件"))
    print(f"✓ 教师辅助功能正常: {msg[:20]}...")
except Exception as e:
    print(f"✗ 教师辅助功能失败: {e}")
    sys.exit(1)

# 测试8: 输入验证
try:
    from ui.input_validator import InputValidator
    validator = InputValidator()
    result = validator.validate_tolerance_parameter("0.6")
    print(f"✓ 输入验证正常: {result['valid']}")
except Exception as e:
    print(f"✗ 输入验证失败: {e}")
    sys.exit(1)

# 测试9: 交互向导
try:
    from ui.interactive_guide import InteractiveGuide
    guide = InteractiveGuide()
    print("✓ 交互向导初始化成功")
except Exception as e:
    print(f"✗ 交互向导失败: {e}")
    sys.exit(1)

print("\n=== 所有核心功能测试通过! ===")
print("项目编译和运行正常")
