#!/usr/bin/env python3
"""
测试修复脚本
验证所有代码修复是否成功

合理性说明：
- 该文件更偏向“修复验收清单”，不是严格意义的单元测试。
- 运行方式为脚本（main），用于快速检查：
    - 关键常量是否存在
    - 关键模块是否可导入
    - 关键依赖是否安装
    - 配置加载器是否可用
- 该脚本不会写入项目文件，仅会读取配置/源文件并打印结果。
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)

def test_hardcoding_fixes():
    """测试硬编码问题是否解决"""
    print("测试硬编码问题修复...")
    try:
        from config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR, STUDENT_PHOTOS_DIR, CLASS_PHOTOS_DIR
        print('✓ 硬编码问题测试通过')
        print(f'  默认输入数据目录: {DEFAULT_INPUT_DIR}')
        print(f'  默认输出目录: {DEFAULT_OUTPUT_DIR}')
        print(f'  默认日志目录: {DEFAULT_LOG_DIR}')
        print(f'  学生照片目录名: {STUDENT_PHOTOS_DIR}')
        print(f'  课堂照片目录名: {CLASS_PHOTOS_DIR}')
        return True
    except Exception as e:
        print(f'✗ 硬编码问题测试失败: {e}')
        return False

def test_import_consistency():
    """测试导入依赖是否一致"""
    print("\n测试导入依赖一致性...")
    try:
        from student_manager import StudentManager
        from face_recognizer import FaceRecognizer
        from file_organizer import FileOrganizer
        from utils import setup_logger, is_supported_image_file
        print('✓ 导入依赖一致性测试通过')
        return True
    except Exception as e:
        print(f'✗ 导入依赖一致性测试失败: {e}')
        return False

def test_data_structure_consistency():
    """测试数据结构一致性"""
    print("\n测试数据结构一致性...")
    try:
        from student_manager import StudentManager
        sm = StudentManager('input')
        students = sm.get_all_students()
        student_names = sm.get_student_names()
        
        print(f'✓ 数据结构一致性测试通过')
        print(f'  学生数量: {len(students)}')
        print(f'  学生姓名: {student_names}')
        
        # 检查数据结构
        if not isinstance(students, list):
            print('  数据结构错误: students不是列表')
            return False

        if students:
            first_student = students[0]
            if 'name' in first_student and 'photo_paths' in first_student:
                print('  数据结构正确: 包含name和photo_paths字段')
                return True
            else:
                print('  数据结构错误: 缺少必要字段')
                return False
        else:
            print('  提示: 当前没有学生数据，跳过字段检查')
            return True
    except Exception as e:
        print(f'✗ 数据结构一致性测试失败: {e}')
        return False

def test_dependency_management():
    """测试依赖管理"""
    print("\n测试依赖管理...")
    try:
        import subprocess
        import sys
        
        # 使用pip list检查依赖
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'✗ 依赖管理测试失败: 无法获取包列表')
            return False
            
        installed = result.stdout.lower()
        required_packages = ['face-recognition', 'pillow', 'numpy', 'tqdm']
        
        missing_packages = []
        for pkg in required_packages:
            if pkg.lower() not in installed:
                # 尝试导入测试
                try:
                    __import__(pkg.replace('-', '_'))
                except ImportError:
                    missing_packages.append(pkg)
        
        if not missing_packages:
            print('✓ 依赖管理测试通过')
            return True
        else:
            print(f'✗ 依赖管理测试失败: 缺少包 {missing_packages}')
            return False
    except Exception as e:
        print(f'✗ 依赖管理测试失败: {e}')
        return False

def test_config_loader():
    """测试配置加载器"""
    print("\n测试配置加载器...")
    try:
        from config_loader import ConfigLoader
        config_loader = ConfigLoader()
        
        input_dir = config_loader.get_input_dir()
        output_dir = config_loader.get_output_dir()
        log_dir = config_loader.get_log_dir()
        tolerance = config_loader.get_tolerance()
        
        if input_dir and output_dir and log_dir and tolerance is not None:
            print('✓ 配置加载器测试通过')
            print(f'  输入数据目录: {input_dir}')
            print(f'  输出目录: {output_dir}')
            print(f'  日志目录: {log_dir}')
            print(f'  识别阈值: {tolerance}')
            return True
        else:
            print('✗ 配置加载器测试失败: 配置值不正确')
            return False
    except Exception as e:
        print(f'✗ 配置加载器测试失败: {e}')
        return False

def main():
    """运行所有测试"""
    print("开始验证代码修复...\n")
    
    all_passed = True
    
    if not test_hardcoding_fixes():
        all_passed = False
    
    if not test_import_consistency():
        all_passed = False
    
    if not test_data_structure_consistency():
        all_passed = False
    
    if not test_dependency_management():
        all_passed = False
    
    if not test_config_loader():
        all_passed = False
    
    print("\n测试结果:")
    if all_passed:
        print("✓ 所有修复验证通过！")
        return 0
    else:
        print("✗ 部分修复验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())