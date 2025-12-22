#!/usr/bin/env python3
"""
教师帮助系统测试
测试所有面向教师的帮助功能和用户体验

合理性说明：
- 该文件属于“体验/文案/协作”层面的回归测试，主要验证：
    - 关键模块可导入
    - 关键文案/表情符号/解决方案提示存在且格式合理
    - InteractiveGuide 在自动化环境下不会阻塞
- 测试过程中会设置 GUIDE_FORCE_AUTO，结束后会恢复原值，避免影响同进程其他测试。
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加 src 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)

class TeacherHelpSystemTester:
    """教师帮助系统测试器"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self._prev_guide_force_auto = os.environ.get("GUIDE_FORCE_AUTO")
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp(prefix='teacher_help_test_')
        os.environ["GUIDE_FORCE_AUTO"] = "true"  # 强制自动回答，避免测试阻塞
        print(f"📁 测试环境创建于: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """清理测试环境"""
        if self._prev_guide_force_auto is None:
            os.environ.pop("GUIDE_FORCE_AUTO", None)
        else:
            os.environ["GUIDE_FORCE_AUTO"] = self._prev_guide_force_auto
            
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🗑️ 测试环境已清理")
    
    def run_test(self, test_name, test_func):
        """运行单个测试"""
        print(f"\n🧪 测试: {test_name}")
        print("-" * 50)
        
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} - 通过")
                self.test_results.append((test_name, True, ""))
                return True
            else:
                print(f"❌ {test_name} - 失败")
                self.test_results.append((test_name, False, "测试返回False"))
                return False
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
            self.test_results.append((test_name, False, str(e)))
            return False
    
    def test_teacher_helper_module(self):
        """测试教师辅助模块"""
        print("🔍 测试教师辅助模块...")
        
        try:
            from ui.teacher_helper import TeacherHelper, create_friendly_exception_handler
            
            helper = TeacherHelper()
            print("✅ TeacherHelper 类创建成功")
            
            # 测试各种错误类型的友好消息
            error_types = [
                ('FileNotFoundError', 'test.jpg not found'),
                ('PermissionError', 'Permission denied'),
                ('MemoryError', 'Out of memory'),
                ('ImportError', 'Module not found'),
            ]
            
            for error_type, error_msg in error_types:
                try:
                    if error_type == 'FileNotFoundError':
                        raise FileNotFoundError(error_msg)
                    elif error_type == 'PermissionError':
                        raise PermissionError(error_msg)
                    elif error_type == 'MemoryError':
                        raise MemoryError(error_msg)
                    elif error_type == 'ImportError':
                        raise ImportError(error_msg)
                except Exception as e:
                    friendly_msg = helper.get_friendly_error(e, "测试上下文")
                    if "📁" in friendly_msg or "🔒" in friendly_msg or "🧠" in friendly_msg or "📦" in friendly_msg:
                        print(f"✅ {error_type} 友好消息格式正确")
                    else:
                        print(f"❌ {error_type} 友好消息格式不正确")
                        return False
            
            return True
            
        except Exception as e:
            print(f"❌ 教师辅助模块测试失败: {e}")
            return False
    
    def test_input_validator(self):
        """测试输入验证器"""
        print("🔍 测试输入验证器...")
        
        try:
            from ui.input_validator import validator
            
            # 测试照片文件名验证
            valid_names = ['张三_1.jpg', '李四.jpg', 'Alice.jpg', 'Bob_2.png']
            invalid_names = ['Alice!.jpg', '张三__1.jpg', '张三_01.jpg']
            
            for name in valid_names:
                result = validator.validate_photo_name(name)
                if not result['valid']:
                    print(f"❌ 有效文件名验证失败: {name}")
                    return False
            print("✅ 有效文件名验证通过")
            
            for name in invalid_names:
                result = validator.validate_photo_name(name)
                if result['valid']:
                    print(f"❌ 无效文件名应该被拒绝: {name}")
                    return False
            print("✅ 无效文件名验证通过")
            
            # 测试目录验证
            test_dir = self.temp_dir
            result = validator.validate_directory_exists(test_dir, "测试目录")
            if not result['valid']:
                print(f"❌ 目录验证失败: {test_dir}")
                return False
            print("✅ 目录验证通过")
            
            # 测试阈值参数验证
            valid_tolerances = ['0.5', '0.6', '0.8']
            invalid_tolerances = ['1.5', '-0.1', 'abc']
            
            for tolerance in valid_tolerances:
                result = validator.validate_tolerance_parameter(tolerance)
                if not result['valid']:
                    print(f"❌ 有效阈值验证失败: {tolerance}")
                    return False
            print("✅ 有效阈值验证通过")
            
            for tolerance in invalid_tolerances:
                result = validator.validate_tolerance_parameter(tolerance)
                if result['valid']:
                    print(f"❌ 无效阈值应该被拒绝: {tolerance}")
                    return False
            print("✅ 无效阈值验证通过")
            
            return True
            
        except Exception as e:
            print(f"❌ 输入验证器测试失败: {e}")
            return False
    
    def test_interactive_guide(self):
        """测试交互式指导"""
        print("🔍 测试交互式指导...")
        
        try:
            from ui.interactive_guide import InteractiveGuide
            
            guide = InteractiveGuide()
            print("✅ InteractiveGuide 创建成功")
            
            # 测试环境检查功能
            result = guide.check_environment()
            print(f"✅ 环境检查功能正常: {result}")
            
            # 测试目录检查功能
            test_dir = os.path.join(self.temp_dir, 'input')
            os.makedirs(test_dir, exist_ok=True)
            os.makedirs(os.path.join(test_dir, 'student_photos'), exist_ok=True)
            os.makedirs(os.path.join(test_dir, 'class_photos'), exist_ok=True)
            
            # 切换到测试目录进行测试
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            try:
                result = guide.check_directories()
                print(f"✅ 目录检查功能正常: {result}")
            finally:
                os.chdir(original_cwd)
            
            return True
            
        except Exception as e:
            print(f"❌ 交互式指导测试失败: {e}")
            return False
    
    def test_operation_guides(self):
        """测试操作指南"""
        print("🔍 测试操作指南...")
        
        try:
            from ui.interactive_guide import show_operation_guide
            from ui.input_validator import show_operation_guide as validator_guide
            
            # 测试各种指南类型
            guide_types = [
                'photo_preparation',
                'file_organization', 
                'troubleshooting'
            ]
            
            for guide_type in guide_types:
                guide_content = show_operation_guide(guide_type)
                if not guide_content or len(guide_content) < 100:
                    print(f"❌ 指南内容为空或过短: {guide_type}")
                    return False
                
                if '📸' not in guide_content and '📁' not in guide_content and '🔧' not in guide_content:
                    print(f"❌ 指南内容格式不正确: {guide_type}")
                    return False
                
                print(f"✅ {guide_type} 指南内容正确")
            
            return True
            
        except Exception as e:
            print(f"❌ 操作指南测试失败: {e}")
            return False
    
    def test_friendly_error_messages(self):
        """测试友好错误消息"""
        print("🔍 测试友好错误消息...")
        
        try:
            from ui.teacher_helper import TeacherHelper
            
            helper = TeacherHelper()
            
            # 测试各种错误场景
            test_cases = [
                (FileNotFoundError("test.jpg"), "文件不存在场景"),
                (PermissionError("Access denied"), "权限拒绝场景"),
                (MemoryError("Out of memory"), "内存不足场景"),
                (ImportError("No module named 'test'"), "模块导入错误场景"),
                (Exception("Generic error"), "通用错误场景"),
            ]
            
            for error, description in test_cases:
                try:
                    raise error
                except Exception as e:
                    friendly_msg = helper.get_friendly_error(e, description)
                    
                    # 检查消息格式
                    if not any(emoji in friendly_msg for emoji in ['📁', '🔒', '🧠', '📦', '🌐', '⚙️', '🖼️', '⚠️']):
                        print(f"❌ {description} 消息缺少表情符号")
                        return False
                    
                    if '💡' not in friendly_msg:
                        print(f"❌ {description} 消息缺少解决方案")
                        return False
                    
                    if len(friendly_msg) < 50:
                        print(f"❌ {description} 消息内容过短")
                        return False
                    
                    print(f"✅ {description} 友好消息正确")
            
            return True
            
        except Exception as e:
            print(f"❌ 友好错误消息测试失败: {e}")
            return False
    
    def test_teacher_friendly_tester(self):
        """测试教师友好测试器本身"""
        print("🔍 测试教师友好测试器...")
        
        try:
            # 导入并创建测试器
            from test_teacher_friendly import TeacherFriendlyTester
            
            tester = TeacherFriendlyTester()
            print("✅ TeacherFriendlyTester 创建成功")
            
            # 测试基本环境检查
            result = tester.test_basic_setup()
            print(f"✅ 基本环境检查: {result}")
            
            # 测试依赖包检查
            result = tester.test_dependencies()
            print(f"✅ 依赖包检查: {result}")
            
            # 测试配置文件检查
            result = tester.test_config_file()
            print(f"✅ 配置文件检查: {result}")
            
            return True
            
        except Exception as e:
            print(f"❌ 教师友好测试器测试失败: {e}")
            return False
    
    def test_help_system_integration(self):
        """测试帮助系统集成"""
        print("🔍 测试帮助系统集成...")
        
        try:
            # 测试是否可以导入所有帮助模块
            modules = [
                'ui.teacher_helper',
                'ui.input_validator', 
                'ui.interactive_guide'
            ]
            
            for module_name in modules:
                try:
                    __import__(module_name)
                    print(f"✅ {module_name} 模块导入成功")
                except ImportError as e:
                    print(f"❌ {module_name} 模块导入失败: {e}")
                    return False
            
            # 测试模块之间的协作
            from ui.input_validator import validator
            from ui.teacher_helper import TeacherHelper
            
            # 模拟一个完整的用户帮助场景
            validation_result = validator.validate_photo_name('张三_1.jpg')
            if not validation_result['valid']:
                print("❌ 验证器和辅助器协作失败")
                return False
            
            helper = TeacherHelper()
            test_error = FileNotFoundError("测试文件不存在")
            friendly_msg = helper.get_friendly_error(test_error)
            
            if not friendly_msg or len(friendly_msg) < 50:
                print("❌ 帮助系统集成测试失败")
                return False
            
            print("✅ 帮助系统集成正常")
            return True
            
        except Exception as e:
            print(f"❌ 帮助系统集成测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🎯 开始教师帮助系统测试")
        print("=" * 60)
        
        tests = [
            ("教师辅助模块", self.test_teacher_helper_module),
            ("输入验证器", self.test_input_validator),
            ("交互式指导", self.test_interactive_guide),
            ("操作指南", self.test_operation_guides),
            ("友好错误消息", self.test_friendly_error_messages),
            ("教师友好测试器", self.test_teacher_friendly_tester),
            ("帮助系统集成", self.test_help_system_integration),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        self.show_summary()
        
        # 清理测试环境
        self.cleanup_test_environment()
        
        # 返回测试结果
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        return passed == total
    
    def show_summary(self):
        """显示测试总结"""
        print("\n" + "=" * 60)
        print("📊 教师帮助系统测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"📈 总测试数: {total}")
        print(f"✅ 通过测试: {passed}")
        print(f"❌ 失败测试: {total - passed}")
        print(f"📊 通过率: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 所有帮助系统测试通过！")
            print("💡 教师用户友好的功能全部正常工作")
        else:
            print("\n⚠️ 部分测试未通过")
            
            print("\n❌ 失败的测试项目：")
            for test_name, result, error_msg in self.test_results:
                if not result:
                    print(f"   • {test_name}: {error_msg}")
        
        print("=" * 60)

def main():
    """主函数"""
    print("🏫 主日学课堂照片整理工具 - 教师帮助系统测试")
    print("=" * 60)
    print("这个测试会验证所有面向教师的帮助功能")
    print("包括错误提示、操作指导、输入验证等")
    print("=" * 60)
    
    tester = TeacherHelpSystemTester()
    success = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 教师帮助系统完全正常！")
        print("💡 所有用户友好的功能都已就绪")
        print("👨‍🏫 教师用户将获得良好的使用体验")
    else:
        print("⚠️ 部分帮助功能需要修复")
        print("💡 请检查失败的测试项目并进行修复")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())