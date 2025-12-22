#!/usr/bin/env python3
"""
简化的测试脚本，验证所有代码修复是否成功
"""

import os
import sys
import traceback
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)
parent_dir = str(PROJECT_ROOT)

def run_tests():
    """运行所有测试"""
    print("开始验证代码修复...\n")
    
    all_passed = True
    
    # 测试1: 硬编码问题修复
    print("测试1: 硬编码问题修复")
    try:
        import config
        print(f"  ✓ DEFAULT_INPUT_DIR: {config.DEFAULT_INPUT_DIR}")
        print(f"  ✓ DEFAULT_OUTPUT_DIR: {config.DEFAULT_OUTPUT_DIR}")
        print(f"  ✓ STUDENT_PHOTOS_DIR: {config.STUDENT_PHOTOS_DIR}")
        print("  ✓ 硬编码问题修复通过")
    except Exception as e:
        print(f"  ✗ 硬编码问题修复失败: {e}")
        all_passed = False
    
    # 测试2: 导入依赖一致性
    print("\n测试2: 导入依赖一致性")
    try:
        from student_manager import StudentManager
        from face_recognizer import FaceRecognizer
        from file_organizer import FileOrganizer
        from utils import setup_logger, is_supported_image_file
        from config_loader import ConfigLoader
        print("  ✓ 所有模块导入成功")
        print("  ✓ 导入依赖一致性通过")
    except Exception as e:
        print(f"  ✗ 导入依赖一致性失败: {e}")
        all_passed = False
    
    # 测试3: 数据结构一致性
    print("\n测试3: 数据结构一致性")
    try:
        from student_manager import StudentManager
        sm = StudentManager(os.path.join(parent_dir, 'input'))
        students = sm.get_all_students()
        student_names = sm.get_student_names()
        
        print(f"  ✓ 学生数量: {len(students)}")
        print(f"  ✓ 学生姓名: {student_names}")
        
        if students and isinstance(students, list):
            print("  ✓ students是列表类型")
            if students and 'name' in students[0] and 'photo_paths' in students[0]:
                print("  ✓ 数据结构包含必要字段")
                print("  ✓ 数据结构一致性通过")
            else:
                print("  ✗ 数据结构缺少必要字段")
                all_passed = False
        else:
            print("  ✗ students不是列表类型")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 数据结构一致性失败: {e}")
        traceback.print_exc()
        all_passed = False
    
    # 测试4: 配置加载器
    print("\n测试4: 配置加载器")
    try:
        from config_loader import ConfigLoader
        config_loader = ConfigLoader(os.path.join(parent_dir, 'config.json'))
        classroom_dir = config_loader.get_input_dir()
        output_dir = config_loader.get_output_dir()
        tolerance = config_loader.get_tolerance()
        
        print(f"  ✓ 输入数据目录: {classroom_dir}")
        print(f"  ✓ 输出目录: {output_dir}")
        print(f"  ✓ 识别阈值: {tolerance}")
        print("  ✓ 配置加载器通过")
    except Exception as e:
        print(f"  ✗ 配置加载器失败: {e}")
        all_passed = False
    
    # 测试5: run.py硬编码修复
    print("\n测试5: run.py硬编码修复")
    try:
        with open(os.path.join(parent_dir, 'run.py'), 'r') as f:
            content = f.read()
        
        if 'default="课堂"' in content:
            print("  ✗ run.py中仍有硬编码中文路径")
            all_passed = False
        else:
            print("  ✓ run.py中硬编码问题已修复")
    except Exception as e:
        print(f"  ✗ run.py硬编码检查失败: {e}")
        all_passed = False
    
    print("\n测试结果:")
    if all_passed:
        print("✓ 所有修复验证通过！")
        return 0
    else:
        print("✗ 部分修复验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())