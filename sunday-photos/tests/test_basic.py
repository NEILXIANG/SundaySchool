#!/usr/bin/env python3
"""
基本测试脚本
验证修改后的代码结构和基本功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加src目录到Python路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
sys.path.insert(0, str(PROJECT_ROOT / 'tests'))
os.chdir(PROJECT_ROOT)

def test_imports():
    """测试所有模块导入是否正常"""
    print("测试模块导入...")
    
    try:
        from core.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR
        print("✓ config模块导入成功")
    except ImportError as e:
        print(f"✗ config模块导入失败: {e}")
        assert False, f"config模块导入失败: {e}"
    
    try:
        from student_manager import StudentManager
        print("✓ student_manager模块导入成功")
    except ImportError as e:
        print(f"✗ student_manager模块导入失败: {e}")
        assert False, f"student_manager模块导入失败: {e}"
    
    try:
        from face_recognizer import FaceRecognizer
        print("✓ face_recognizer模块导入成功")
    except ImportError as e:
        print(f"✗ face_recognizer模块导入失败: {e}")
        assert False, f"face_recognizer模块导入失败: {e}"
    
    try:
        from file_organizer import FileOrganizer
        print("✓ file_organizer模块导入成功")
    except ImportError as e:
        print(f"✗ file_organizer模块导入失败: {e}")
        assert False, f"file_organizer模块导入失败: {e}"
    
    try:
        from utils import setup_logger, is_supported_image_file
        print("✓ utils模块导入成功")
    except ImportError as e:
        print(f"✗ utils模块导入失败: {e}")
        assert False, f"utils模块导入失败: {e}"
    
    try:
        from config_loader import ConfigLoader
        print("✓ config_loader模块导入成功")
    except ImportError as e:
        print(f"✗ config_loader模块导入失败: {e}")
        assert False, f"config_loader模块导入失败: {e}"

def test_student_manager():
    """测试StudentManager基本功能"""
    print("\n测试StudentManager...")
    
    # 在每个函数内导入需要的类
    from student_manager import StudentManager
    
    # 创建临时目录结构
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试目录
        input_dir = Path(temp_dir) / "input"
        student_photos_dir = input_dir / "student_photos"
        student_photos_dir.mkdir(parents=True)
        
        # 创建测试图片文件（文件夹模式：student_photos/<学生名>/...）
        from testdata_builder import write_jpeg

        write_jpeg(student_photos_dir / "Student1" / "a.jpg", "Student1_a", seed=1)
        write_jpeg(student_photos_dir / "Student1" / "b.jpg", "Student1_b", seed=2)
        write_jpeg(student_photos_dir / "Student2" / "1.jpg", "Student2_1", seed=3)
        
        try:
            # 测试StudentManager
            student_manager = StudentManager(str(input_dir))
            students = student_manager.get_all_students()
            student_names = student_manager.get_student_names()

            assert len(students) == 2 and len(student_names) == 2, (
                f"StudentManager数据不正确: 学生数={len(students)}, 学生名数={len(student_names)}"
            )
            print("✓ StudentManager基本功能正常")
        except Exception as e:
            print(f"✗ StudentManager测试失败: {e}")
            raise AssertionError(f"StudentManager测试失败: {e}") from e

def test_config_loader():
    """测试ConfigLoader基本功能"""
    print("\n测试ConfigLoader...")
    
    try:
        from config_loader import ConfigLoader
        config_loader = ConfigLoader()
        input_dir = config_loader.get_input_dir()
        output_dir = config_loader.get_output_dir()
        log_dir = config_loader.get_log_dir()
        tolerance = config_loader.get_tolerance()
        
        assert input_dir and output_dir and log_dir and tolerance, (
            f"ConfigLoader配置不正确: input_dir={input_dir}, output_dir={output_dir}, log_dir={log_dir}, tolerance={tolerance}"
        )
        print("✓ ConfigLoader基本功能正常")
    except Exception as e:
        print(f"✗ ConfigLoader测试失败: {e}")
        raise AssertionError(f"ConfigLoader测试失败: {e}") from e

def test_config_file():
    """测试配置文件加载"""
    print("\n测试配置文件加载...")
    
    try:
        from config_loader import ConfigLoader
        config_file = PROJECT_ROOT / "config.json"
        assert config_file.exists(), "配置文件不存在"

        config_loader = ConfigLoader(str(config_file))
        photo_processing = config_loader.get('photo_processing')
        face_recognition = config_loader.get('face_recognition')

        assert photo_processing and face_recognition, (
            f"配置文件内容不正确: photo_processing={photo_processing}, face_recognition={face_recognition}"
        )
        print("✓ 配置文件加载正常")
    except Exception as e:
        print(f"✗ 配置文件测试失败: {e}")
        raise AssertionError(f"配置文件测试失败: {e}") from e

def main():
    """运行所有测试"""
    print("开始基本测试...\n")
    
    all_passed = True

    tests = [
        ("模块导入", test_imports),
        ("StudentManager", test_student_manager),
        ("ConfigLoader", test_config_loader),
        ("配置文件", test_config_file),
    ]

    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            all_passed = False
            print(f"✗ {name} 断言失败: {e}")
        except Exception as e:
            all_passed = False
            print(f"✗ {name} 测试异常: {e}")
    
    print("\n测试结果:")
    if all_passed:
        print("✓ 所有基本测试通过")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())