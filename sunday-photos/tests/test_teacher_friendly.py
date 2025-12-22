#!/usr/bin/env python3
"""
教师友好测试用例
专门针对没有计算机基础的老师设计的用户友好性测试
"""

import os
import sys
from pathlib import Path
import traceback
from pathlib import Path

# 添加 src 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)

class TeacherFriendlyTester:
    """教师友好的测试器"""
    
    def __init__(self):
        self.test_results = []
        self.error_messages = []
    
    def run_test(self, test_name, test_func):
        """运行单个测试"""
        print(f"\n🧪 正在测试: {test_name}")
        print("=" * 50)
        
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
            error_msg = self.get_friendly_error_message(e, test_name)
            print(f"❌ {test_name} - 出现问题")
            print(f"💡 帮助信息: {error_msg}")
            self.test_results.append((test_name, False, error_msg))
            return False
    
    def get_friendly_error_message(self, error, test_name):
        """获取友好的错误信息"""
        error_str = str(error)
        
        # 文件相关错误
        if "FileNotFoundError" in error_str or "找不到文件" in error_str:
            return "😕 找不到文件或文件夹\n   💡 请检查：\n   • 确保在正确的文件夹中运行程序\n   • 检查文件夹名是否拼写正确\n   • 确保文件确实存在"
        
        # 权限错误
        if "Permission denied" in error_str or "权限" in error_str:
            return "🔒 没有权限访问文件\n   💡 请尝试：\n   • 关闭可能正在使用这些文件的程序\n   • 以管理员身份运行程序\n   • 检查文件夹是否为只读"
        
        # 模块导入错误
        if "ImportError" in error_str or "ModuleNotFoundError" in error_str:
            return "📦 缺少必要的程序组件\n   💡 请运行：\n   • pip install -r requirements.txt\n   • 确保已正确安装所有依赖包"
        
        # 人脸识别相关错误
        if "face_recognition" in error_str.lower():
            return "👤 人脸识别功能出现问题\n   💡 请检查：\n   • 照片是否包含清晰的人脸\n   • 照片格式是否支持（建议使用.jpg）\n   • 照片文件是否损坏"
        
        # 网络相关错误
        if "network" in error_str.lower() or "connection" in error_str.lower():
            return "🌐 网络连接问题\n   💡 请检查：\n   • 网络连接是否正常\n   • 防火墙是否阻止程序访问网络"
        
        # 内存相关错误
        if "MemoryError" in error_str or "内存" in error_str:
            return "🧠 电脑内存不足\n   💡 请尝试：\n   • 关闭其他不需要的程序\n   • 减少一次处理的照片数量\n   • 重启电脑释放内存"
        
        # 通用错误信息
        return f"⚠️ 程序遇到了问题\n   💡 建议：\n   • 重新启动程序\n   • 检查输入是否正确\n   • 如果问题持续，请联系技术支持\n   📝 详细错误：{error_str[:100]}..."
    
    def show_summary(self):
        """显示测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        
        passed = sum(1 for _, result, _ in self.test_results if result)
        total = len(self.test_results)
        
        print(f"📈 总测试数: {total}")
        print(f"✅ 通过测试: {passed}")
        print(f"❌ 失败测试: {total - passed}")
        print(f"📊 通过率: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 所有测试都通过了！程序运行正常！")
        else:
            print("\n⚠️ 部分测试未通过，请查看上面的帮助信息进行修复")
            
            print("\n❌ 失败的测试项目：")
            for test_name, result, error_msg in self.test_results:
                if not result:
                    print(f"   • {test_name}")
                    print(f"     {error_msg}")
    
    def test_basic_setup(self):
        """测试基本设置"""
        print("🔍 检查基本环境设置...")
        
        # 检查Python版本
        if sys.version_info < (3, 7):
            print("❌ Python版本太旧")
            return False
        
        print(f"✅ Python版本正常 ({sys.version.split()[0]})")
        
        # 检查项目目录结构
        required_dirs = ['input', 'output', 'src']
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                print(f"❌ 缺少必要文件夹: {dir_name}")
                return False
            print(f"✅ 找到文件夹: {dir_name}")
        
        # 检查学生照片目录
        student_photos_dir = os.path.join('input', 'student_photos')
        if not os.path.exists(student_photos_dir):
            print("❌ 缺少学生照片文件夹")
            print("💡 请创建 input/student_photos 文件夹")
            return False
        
        print("✅ 基本设置检查通过")
        return True
    
    def test_student_photos(self):
        """测试学生照片"""
        print("👥 检查学生照片...")
        
        student_photos_dir = os.path.join('input', 'student_photos')
        if not os.path.exists(student_photos_dir):
            print("❌ 学生照片文件夹不存在")
            return False
        
        photos = [f for f in os.listdir(student_photos_dir) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if not photos:
            print("⚠️ 学生照片文件夹中没有找到照片（可选，建议添加参考照提升识别准确度）")
            return True
        
        print(f"✅ 找到 {len(photos)} 张学生照片")
        
        # 检查文件名格式（允许姓名或姓名_序号）
        try:
            from ui.input_validator import validator
            for photo in photos[:3]:
                result = validator.validate_photo_name(photo)
                if not result['valid']:
                    print(f"❌ 照片文件名格式不正确: {photo}")
                    print("💡 建议使用：姓名.jpg 或 姓名_序号.jpg（如：Alice.jpg 或 张三_1.jpg）")
                    return False
        except Exception:
            pass
        
        print("✅ 学生照片检查通过")
        return True
    
    def test_dependencies(self):
        """测试依赖包"""
        print("📦 检查程序依赖...")
        
        required_packages = ['face_recognition', 'PIL', 'numpy', 'tqdm']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} - 已安装")
            except ImportError:
                print(f"❌ {package} - 未安装")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n💡 安装缺失的包：")
            print("   pip install -r requirements.txt")
            print(f"   或单独安装：pip install {' '.join(missing_packages)}")
            return False
        
        print("✅ 所有依赖包检查通过")
        return True
    
    def test_config_file(self):
        """测试配置文件"""
        print("⚙️ 检查配置文件...")
        
        config_file = 'config.json'
        if not os.path.exists(config_file):
            print("❌ 配置文件不存在")
            print("💡 程序会使用默认配置，但建议创建config.json文件")
            return True  # 不是致命错误
        
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            required_keys = ['input_dir', 'output_dir', 'tolerance']
            for key in required_keys:
                if key not in config:
                    print(f"❌ 配置文件缺少: {key}")
                    return False
                print(f"✅ 配置项 {key}: {config[key]}")
            
            print("✅ 配置文件检查通过")
            return True
            
        except Exception as e:
            print(f"❌ 配置文件格式错误: {e}")
            print("💡 请检查config.json文件格式是否正确")
            return False
    
    def test_output_permissions(self):
        """测试输出权限"""
        print("📁 检查输出文件夹权限...")
        
        output_dir = 'output'
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 测试写入权限
        test_file = os.path.join(output_dir, 'test_permission.tmp')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("✅ 输出文件夹权限正常")
            return True
        except Exception as e:
            print(f"❌ 无法在输出文件夹中创建文件: {e}")
            print("💡 请检查文件夹权限或选择其他输出文件夹")
            return False
    
    def test_student_manager(self):
        """测试学生管理器"""
        print("👨‍🏫 测试学生信息管理...")
        
        try:
            from student_manager import StudentManager
            
            sm = StudentManager('input')
            students = sm.get_all_students()
            
            if not isinstance(students, list):
                print("❌ 学生数据格式错误")
                return False
            if not students:
                print("⚠️ 当前没有学生信息（可选，建议添加参考照以启用识别）")
                return True
            
            print(f"✅ 成功加载 {len(students)} 名学生信息")
            
            # 检查数据结构
            if isinstance(students, list) and len(students) > 0:
                student = students[0]
                if 'name' in student and 'photo_paths' in student:
                    print("✅ 学生信息结构正确")
                    return True
                else:
                    print("❌ 学生信息结构不完整")
                    return False
            else:
                print("❌ 学生数据格式错误")
                return False
                
        except Exception as e:
            print(f"❌ 学生管理器初始化失败: {e}")
            return False
    
    def test_face_recognition(self):
        """测试人脸识别功能"""
        print("👤 测试人脸识别功能...")
        
        try:
            from student_manager import StudentManager
            from face_recognizer import FaceRecognizer
            
            sm = StudentManager('input')
            fr = FaceRecognizer(sm)
            
            print("✅ 人脸识别器初始化成功")
            
            # 检查是否有有效的面部编码（新版使用 known_encodings 缓存）
            encodings = getattr(fr, 'known_encodings', [])
            if encodings:
                count = len(encodings)
                print(f"✅ 成功加载 {count} 个面部编码")
                return True
            else:
                print("⚠️ 人脸识别器没有加载到面部编码，可能参考照片中未检测到人脸")
                print("💡 提示：提供更清晰的学生参考照片或增加样本数量")
                return True  # 作为提示而非致命错误
                
        except Exception as e:
            print(f"❌ 人脸识别功能测试失败: {e}")
            return False
    
    def test_main_program(self):
        """测试主程序"""
        print("🚀 测试主程序初始化...")
        
        try:
            from main import SimplePhotoOrganizer
            
            organizer = SimplePhotoOrganizer()
            
            print("✅ 主程序创建成功")
            
            # 尝试初始化
            success = organizer.initialize()
            
            if success:
                print("✅ 主程序初始化成功")
                return True
            else:
                print("❌ 主程序初始化失败")
                return False
                
        except Exception as e:
            print(f"❌ 主程序测试失败: {e}")
            return False
    
    def test_help_system(self):
        """测试帮助系统"""
        print("📚 测试帮助系统...")
        
        # 测试run.py帮助
        try:
            result = os.system('python run.py --help > /dev/null 2>&1')
            if result == 0:
                print("✅ run.py帮助系统正常")
                help_ok = True
            else:
                print("❌ run.py帮助系统有问题")
                help_ok = False
        except:
            print("❌ 无法测试run.py帮助系统")
            help_ok = False
        
        # 检查README文件
        readme_file = 'README.md'
        if os.path.exists(readme_file):
            print("✅ 找到使用说明文档")
            doc_ok = True
        else:
            print("❌ 没有找到使用说明文档")
            doc_ok = False
        
        return help_ok and doc_ok
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🎯 开始教师友好性测试")
        print("这个测试会检查程序是否易于教师使用")
        print("=" * 60)
        
        tests = [
            ("基本环境检查", self.test_basic_setup),
            ("学生照片检查", self.test_student_photos),
            ("依赖包检查", self.test_dependencies),
            ("配置文件检查", self.test_config_file),
            ("输出权限检查", self.test_output_permissions),
            ("学生管理器测试", self.test_student_manager),
            ("人脸识别测试", self.test_face_recognition),
            ("主程序测试", self.test_main_program),
            ("帮助系统测试", self.test_help_system),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        self.show_summary()
        
        # 返回是否所有关键测试都通过
        critical_tests = ["基本环境检查", "依赖包检查", "学生管理器测试"]
        critical_passed = all(
            result for test_name, result, _ in self.test_results 
            if test_name in critical_tests
        )
        
        return critical_passed

def main():
    """主函数"""
    print("👨‍🏫 主日学课堂照片整理工具 - 教师友好性测试")
    print("这个测试会帮助您检查程序是否准备就绪")
    print("=" * 60)
    
    tester = TeacherFriendlyTester()
    success = tester.run_all_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 恭喜！程序已经准备好使用了！")
        print("💡 现在您可以运行 'python run.py' 开始整理照片")
    else:
        print("⚠️ 还有一些问题需要解决才能正常使用程序")
        print("💡 请按照上面的建议进行修复，然后重新运行测试")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())