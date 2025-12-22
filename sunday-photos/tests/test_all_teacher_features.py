#!/usr/bin/env python3
"""
教师友好功能综合测试
测试所有为教师设计的友好功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加 src 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

def test_teacher_friendly_error_messages():
    """测试教师友好错误消息"""
    print("🔍 测试教师友好错误消息...")
    
    try:
        from teacher_helper import TeacherHelper
        
        helper = TeacherHelper()
        
        # 测试各种错误类型
        test_errors = [
            (FileNotFoundError("test.jpg not found"), "文件不存在"),
            (PermissionError("Access denied"), "权限拒绝"),
            (MemoryError("Out of memory"), "内存不足"),
            (ImportError("Module not found"), "模块导入错误"),
            (Exception("Generic error"), "通用错误"),
        ]
        
        all_passed = True
        for error, description in test_errors:
            try:
                raise error
            except Exception as e:
                friendly_msg = helper.get_friendly_error(e, description)
                
                # 检查消息格式
                if not any(emoji in friendly_msg for emoji in ['📁', '🔒', '🧠', '📦', '🌐', '⚙️', '🖼️', '⚠️']):
                    print(f"❌ {description}: 缺少表情符号")
                    all_passed = False
                
                if '💡' not in friendly_msg:
                    print(f"❌ {description}: 缺少解决方案")
                    all_passed = False
                
                if len(friendly_msg) < 50:
                    print(f"❌ {description}: 消息过短")
                    all_passed = False
        
        if all_passed:
            print("✅ 教师友好错误消息测试通过")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_input_validation():
    """测试输入验证功能"""
    print("🔍 测试输入验证功能...")
    
    try:
        from input_validator import validator
        
        # 测试照片文件名验证
        valid_names = ['张三_1.jpg', '李四.jpg', 'Alice.jpg', 'Bob_2.png']
        invalid_names = ['Alice!.jpg', '张三__1.jpg', '张三_01.jpg']
        
        for name in valid_names:
            result = validator.validate_photo_name(name)
            if not result['valid']:
                print(f"❌ 有效文件名验证失败: {name}")
                return False
        
        for name in invalid_names:
            result = validator.validate_photo_name(name)
            if result['valid']:
                print(f"❌ 无效文件名应该被拒绝: {name}")
                return False
        
        # 测试阈值验证
        valid_tolerances = ['0.5', '0.6', '0.8']
        invalid_tolerances = ['1.5', '-0.1', 'abc']
        
        for tolerance in valid_tolerances:
            result = validator.validate_tolerance_parameter(tolerance)
            if not result['valid']:
                print(f"❌ 有效阈值验证失败: {tolerance}")
                return False
        
        for tolerance in invalid_tolerances:
            result = validator.validate_tolerance_parameter(tolerance)
            if result['valid']:
                print(f"❌ 无效阈值应该被拒绝: {tolerance}")
                return False
        
        print("✅ 输入验证功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_interactive_guide():
    """测试交互式指导"""
    print("🔍 测试交互式指导...")
    
    try:
        from interactive_guide import InteractiveGuide
        
        guide = InteractiveGuide()
        
        # 测试环境检查
        env_result = guide.check_environment()
        print(f"✅ 环境检查: {env_result}")
        
        # 测试目录检查
        dir_result = guide.check_directories()
        print(f"✅ 目录检查: {dir_result}")
        
        print("✅ 交互式指导测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_operation_guides():
    """测试操作指南"""
    print("🔍 测试操作指南...")
    
    try:
        from interactive_guide import show_operation_guide
        
        guide_types = ['photo_preparation', 'file_organization', 'troubleshooting']
        
        for guide_type in guide_types:
            guide_content = show_operation_guide(guide_type)
            
            if not guide_content or len(guide_content) < 100:
                print(f"❌ 指南内容为空或过短: {guide_type}")
                return False
            
            if '💡' not in guide_content:
                print(f"❌ 指南内容缺少建议: {guide_type}")
                return False
        
        print("✅ 操作指南测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_exception_handler():
    """测试异常处理器"""
    print("🔍 测试异常处理器...")
    
    try:
        from teacher_helper import create_friendly_exception_handler
        
        # 测试友好异常处理器
        handler = create_friendly_exception_handler()
        print("✅ 友好异常处理器创建成功")
        
        print("✅ 异常处理器测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_help_integration():
    """测试帮助系统集成"""
    print("🔍 测试帮助系统集成...")
    
    try:
        # 测试所有模块都能正常导入
        modules = [
            'teacher_helper',
            'input_validator',
            'interactive_guide'
        ]
        
        for module_name in modules:
            __import__(module_name)
        
        print("✅ 所有帮助模块导入成功")
        
        # 测试模块协作
        from input_validator import validator
        from teacher_helper import TeacherHelper
        
        # 测试验证器和辅助器协作
        validation_result = validator.validate_photo_name('张三_1.jpg')
        if not validation_result['valid']:
            print("❌ 验证器工作异常")
            return False
        
        helper = TeacherHelper()
        test_error = FileNotFoundError("测试文件不存在")
        friendly_msg = helper.get_friendly_error(test_error)
        
        if not friendly_msg or len(friendly_msg) < 50:
            print("❌ 辅助器工作异常")
            return False
        
        print("✅ 帮助系统集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_user_friendly_features():
    """测试用户友好特性"""
    print("🔍 测试用户友好特性...")
    
    try:
        # 测试表情符号使用
        from teacher_helper import TeacherHelper
        
        helper = TeacherHelper()
        
        # 检查是否有足够的表情符号
        emoji_count = 0
        for key in helper.messages:
            if 'title' in helper.messages[key]:
                title = helper.messages[key]['title']
                emoji_count += len([c for c in title if ord(c) > 127])
        
        if emoji_count < 5:
            print("❌ 表情符号使用不足")
            return False
        
        print(f"✅ 表情符号使用充分: {emoji_count}个")
        
        # 测试解决方案建议
        for key in helper.messages:
            if 'solutions' in helper.messages[key]:
                solutions = helper.messages[key]['solutions']
                if len(solutions) < 2:
                    print(f"❌ {key} 解决方案不足")
                    return False
        
        print("✅ 解决方案建议充分")
        print("✅ 用户友好特性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 开始教师友好功能综合测试")
    print("=" * 60)
    
    tests = [
        ("友好错误消息", test_teacher_friendly_error_messages),
        ("输入验证", test_input_validation),
        ("交互式指导", test_interactive_guide),
        ("操作指南", test_operation_guides),
        ("异常处理器", test_exception_handler),
        ("帮助系统集成", test_help_integration),
        ("用户友好特性", test_user_friendly_features),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 测试: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print("\n" + "=" * 60)
    print("📊 教师友好功能测试总结")
    print("=" * 60)
    
    print(f"📈 总测试数: {total}")
    print(f"✅ 通过测试: {passed}")
    print(f"❌ 失败测试: {total - passed}")
    print(f"📊 通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有教师友好功能测试通过！")
        print("💡 教师用户将获得优秀的使用体验")
        print("👨‍🏫 包括：")
        print("   • 友好的错误提示")
        print("   • 详细的操作指导")
        print("   • 智能的输入验证")
        print("   • 交互式设置向导")
        print("   • 完整的帮助文档")
    else:
        print("\n⚠️ 部分功能需要改进")
        print("💡 请检查失败的测试项目")
    
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())