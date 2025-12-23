#!/usr/bin/env python3
"""
集成测试脚本 - 轻量 smoke/integration 验证。

合理性说明：
- 该文件主要验证“模块可导入 + 核心组件可初始化 + 关键 API 形态不回退”。
- 不要求存在真实图片数据；在沙箱环境下只依赖基础目录结构存在即可。
- 作为脚本运行（非 pytest），用于本项目的沙箱化 runner 逐个执行。
"""

import os
import sys
import traceback
from pathlib import Path

# 添加 src 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)  # 切换到项目根目录

def test_imports():
    """测试所有模块导入"""
    print("=== 测试模块导入 ===")
    
    try:
        from face_recognizer import FaceRecognizer
        print("✓ FaceRecognizer 导入成功")
        
        from student_manager import StudentManager
        print("✓ StudentManager 导入成功")
        
        from file_organizer import FileOrganizer
        print("✓ FileOrganizer 导入成功")
        
        from config_loader import ConfigLoader
        print("✓ ConfigLoader 导入成功")
        
        from main import SimplePhotoOrganizer
        print("✓ SimplePhotoOrganizer 导入成功")
        
        from utils import setup_logger, is_supported_image_file
        print("✓ utils 导入成功")

        return
    except Exception as e:
        print(f"✗ 导入测试失败: {e}")
        traceback.print_exc()
        raise AssertionError(f"导入测试失败: {e}") from e

def test_component_initialization():
    """测试组件初始化"""
    print("\n=== 测试组件初始化 ===")
    
    try:
        from student_manager import StudentManager
        sm = StudentManager('input')
        students = sm.get_all_students()
        print(f"✓ StudentManager 初始化成功，加载了 {len(students)} 名学生")
        
        from face_recognizer import FaceRecognizer
        fr = FaceRecognizer(sm)
        print("✓ FaceRecognizer 初始化成功")
        
        from file_organizer import FileOrganizer
        fo = FileOrganizer('output')
        print("✓ FileOrganizer 初始化成功")
        
        from config_loader import ConfigLoader
        cl = ConfigLoader()
        print("✓ ConfigLoader 初始化成功")

        return
    except Exception as e:
        print(f"✗ 组件初始化测试失败: {e}")
        traceback.print_exc()
        raise AssertionError(f"组件初始化测试失败: {e}") from e

def test_integration():
    """测试系统集成"""
    print("\n=== 测试系统集成 ===")
    
    try:
        from main import SimplePhotoOrganizer
        
        organizer = SimplePhotoOrganizer(
            input_dir='input',
            output_dir='output'
        )
        print("✓ SimplePhotoOrganizer 创建成功")
        
        # 测试初始化
        success = organizer.initialize()
        if success:
            print("✓ 系统初始化成功")
            
            # 测试人脸识别器设置
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                print("✓ 人脸识别器已正确初始化")
                
                # 测试tolerance调整
                organizer.face_recognizer.tolerance = 0.7
                print("✓ tolerance 参数调整成功")
                
            else:
                print("✗ 人脸识别器初始化失败")
                assert False, "人脸识别器初始化失败"
        else:
            print("✗ 系统初始化失败")
            assert False, "系统初始化失败"

        return
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        traceback.print_exc()
        raise AssertionError(f"集成测试失败: {e}") from e

def test_api_methods():
    """测试API方法"""
    print("\n=== 测试API方法 ===")
    
    try:
        from face_recognizer import FaceRecognizer
        import inspect
        
        # 检查recognize_faces方法
        method = getattr(FaceRecognizer, 'recognize_faces', None)
        if method:
            sig = inspect.signature(method)
            if 'return_details' in sig.parameters:
                print("✓ recognize_faces 方法包含 return_details 参数")
            else:
                print("✗ recognize_faces 方法缺少 return_details 参数")
                assert False, "recognize_faces 方法缺少 return_details 参数"
        else:
            print("✗ recognize_faces 方法不存在")
            assert False, "recognize_faces 方法不存在"

        return
    except Exception as e:
        print(f"✗ API方法测试失败: {e}")
        traceback.print_exc()
        raise AssertionError(f"API方法测试失败: {e}") from e

def test_config_integration():
    """测试配置集成"""
    print("\n=== 测试配置集成 ===")
    
    try:
        from config_loader import ConfigLoader
        
        config_loader = ConfigLoader('config.json')
        input_dir = config_loader.get_input_dir()
        output_dir = config_loader.get_output_dir()
        tolerance = config_loader.get_tolerance()
        
        print(f"✓ 配置加载成功: input_dir={input_dir}")
        print(f"✓ 输出目录: {output_dir}")
        print(f"✓ 识别阈值: {tolerance}")

        return
    except Exception as e:
        print(f"✗ 配置集成测试失败: {e}")
        traceback.print_exc()
        raise AssertionError(f"配置集成测试失败: {e}") from e

def main():
    """主测试函数"""
    print("开始集成测试...\n")
    
    tests = [
        ("模块导入", test_imports),
        ("组件初始化", test_component_initialization),
        ("系统集成", test_integration),
        ("API方法", test_api_methods),
        ("配置集成", test_config_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"测试失败: {test_name} - {e}")
        except Exception as e:
            print(f"测试异常: {test_name} - {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有集成测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())