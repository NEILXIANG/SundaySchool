#!/usr/bin/env python3
"""
验证修复后的代码功能
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)

def test_config_loader_integration():
    """测试配置加载器集成"""
    print("测试配置加载器集成...")
    
    try:
        from config_loader import ConfigLoader
        
        # 测试配置加载器
        config_loader = ConfigLoader()
        print(f"✓ ConfigLoader初始化成功")
        
        # 测试配置加载
        classroom_dir = config_loader.get_input_dir()
        output_dir = config_loader.get_output_dir()
        tolerance = config_loader.get_tolerance()
        print(f"✓ 参数解析成功，默认值: input_dir={classroom_dir}, tolerance={tolerance}")
        
        return True
    except Exception as e:
        print(f"✗ 配置加载器集成测试失败: {e}")
        return False

def test_system_initialization():
    """测试系统初始化和tolerance设置"""
    print("\n测试系统初始化和tolerance设置...")
    
    try:
        from main import SimplePhotoOrganizer
        
        # 创建整理器实例
        organizer = SimplePhotoOrganizer(
            input_dir='input',
            output_dir='output'
        )
        print("✓ SimplePhotoOrganizer初始化成功")
        
        # 初始化系统
        if organizer.initialize():
            print("✓ 系统组件初始化成功")
            
            # 测试tolerance设置
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer is not None:
                original_tolerance = organizer.face_recognizer.tolerance
                organizer.face_recognizer.tolerance = 0.7
                new_tolerance = organizer.face_recognizer.tolerance
                
                if abs(new_tolerance - 0.7) < 1e-6:
                    print(f"✓ tolerance设置成功: {original_tolerance} -> {new_tolerance}")
                else:
                    print(f"✗ tolerance设置失败: 仍然是 {new_tolerance}")
            else:
                print("✗ face_recognizer未正确初始化")
                return False
        else:
            print("✗ 系统组件初始化失败")
            return False
            
        return True
    except Exception as e:
        print(f"✗ 系统初始化测试失败: {e}")
        return False

def test_detailed_recognition_status():
    """测试详细识别状态功能"""
    print("\n测试详细识别状态功能...")
    
    try:
        from face_recognizer import FaceRecognizer
        import inspect
        
        # 检查方法参数
        method = getattr(FaceRecognizer, 'recognize_faces', None)
        if method:
            sig = inspect.signature(method)
            if 'return_details' in sig.parameters:
                print("✓ recognize_faces方法包含return_details参数")
            else:
                print("✗ recognize_faces方法缺少return_details参数")
                return False
        else:
            print("✗ recognize_faces方法不存在")
            return False
            
        return True
    except Exception as e:
        print(f"✗ 详细识别状态测试失败: {e}")
        return False

def test_memory_cleanup():
    """测试内存清理功能"""
    print("\n测试内存清理功能...")
    
    try:
        # 检查face_recognizer.py中是否包含内存清理代码
        with open('src/face_recognizer.py', 'r') as f:
            content = f.read()
            
        if 'del image' in content and 'del face_locations' in content:
            print("✓ face_recognizer.py包含内存清理代码")
        else:
            print("✗ face_recognizer.py缺少内存清理代码")
            return False
            
        return True
    except Exception as e:
        print(f"✗ 内存清理测试失败: {e}")
        return False

def test_import_paths():
    """测试导入路径一致性"""
    print("\n测试导入路径一致性...")
    
    try:
        # 检查run.py和test_basic.py中的导入路径
        run_path = PROJECT_ROOT / 'run.py'
        test_basic_path = PROJECT_ROOT / 'tests' / 'test_basic.py'

        run_content = run_path.read_text(encoding='utf-8')
        test_content = test_basic_path.read_text(encoding='utf-8')

        if "sys.path.insert" in run_content and "src" in run_content:
            print("✓ run.py使用一致的导入路径")
        else:
            print("✗ run.py导入路径不一致")
            return False
            
        if "PROJECT_ROOT" in test_content and "sys.path.insert(0, str(PROJECT_ROOT / 'src'))" in test_content:
            print("✓ test_basic.py使用一致的导入路径")
        else:
            print("✗ test_basic.py导入路径不一致")
            return False
            
        return True
    except Exception as e:
        print(f"✗ 导入路径测试失败: {e}")
        return False

def test_directory_structure():
    """测试目录结构一致性"""
    print("\n测试目录结构一致性...")
    
    try:
        # 检查是否存在正确的目录结构
        if os.path.exists('input/student_photos'):
            print("✓ input/student_photos目录存在")
        else:
            print("✗ input/student_photos目录不存在")
            return False
            
        if os.path.exists('input/class_photos'):
            print("✓ input/class_photos目录存在")
        else:
            print("✗ input/class_photos目录不存在")
            return False
            
        return True
    except Exception as e:
        print(f"✗ 目录结构测试失败: {e}")
        return False

def main():
    """运行所有验证测试"""
    print("开始验证修复后的代码功能...\n")
    
    all_passed = True
    
    if not test_config_loader_integration():
        all_passed = False
    
    if not test_system_initialization():
        all_passed = False
    
    if not test_detailed_recognition_status():
        all_passed = False
    
    if not test_memory_cleanup():
        all_passed = False
    
    if not test_import_paths():
        all_passed = False
    
    if not test_directory_structure():
        all_passed = False
    
    print("\n验证结果:")
    if all_passed:
        print("✓ 所有修复验证通过")
        return 0
    else:
        print("✗ 部分修复验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())