"""
交互式指导模块
为教师提供交互式的操作指导和帮助
"""

import os
import sys
from pathlib import Path

from core.config import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_TOLERANCE,
)

class InteractiveGuide:
    """交互式指导类"""
    
    def __init__(self):
        self.setup_guide_steps()
    
    def setup_guide_steps(self):
        """设置指导步骤"""
        self.setup_steps = [
            {
                'name': '环境检查',
                'function': self.check_environment,
                'description': '检查运行环境和依赖包'
            },
            {
                'name': '文件夹检查',
                'function': self.check_directories,
                'description': '检查和创建必要的文件夹'
            },
            {
                'name': '学生照片检查',
                'function': self.check_student_photos,
                'description': '检查学生照片的格式和命名'
            },
            {
                'name': '课堂照片检查',
                'function': self.check_class_photos,
                'description': '检查待整理的课堂照片'
            },
            {
                'name': '配置检查',
                'function': self.check_configuration,
                'description': '检查配置文件'
            }
        ]

    def _prompt_yes_no(self, question, default=True):
        """在非交互环境中自动响应，是避免脚本阻塞"""
        auto_answer = 'y' if default else 'n'
        force_auto = os.environ.get("GUIDE_FORCE_AUTO", "").strip().lower() in ("1", "true", "yes")
        if force_auto or not sys.stdin.isatty():
            print(f"{question}{auto_answer} (自动选择)")
            return default
        while True:
            try:
                choice = input(question).strip().lower()
            except EOFError:
                return default
            if not choice:
                return default
            if choice in ['y', 'yes', '是']:
                return True
            if choice in ['n', 'no', '否']:
                return False
            print("请输入 y 或 n")

    def _wait_for_enter(self, message="按回车键继续..."):
        """在可交互终端等待输入，否则自动继续"""
        if sys.stdin.isatty():
            try:
                input(message)
            except EOFError:
                pass
        else:
            print(f"{message} (自动继续)")
    
    def start_setup_guide(self):
        """开始设置指导"""
        print("""
🎯 主日学课堂照片整理工具 - 交互式设置指南
这个指南将帮助您一步步完成程序设置

⏱️ 预计时间：5-10分钟
📋 步骤：5个主要步骤
💡 需要准备：学生照片文件

按回车键开始...
        """)
        self._wait_for_enter()
        
        all_passed = True
        
        for i, step in enumerate(self.setup_steps, 1):
            print(f"\n{'='*60}")
            print(f"📍 步骤 {i}/{len(self.setup_steps)}: {step['name']}")
            print(f"📝 {step['description']}")
            print(f"{'='*60}")
            
            try:
                result = step['function']()
                if not result:
                    print(f"\n❌ {step['name']} 未通过")
                    
                    if not self._prompt_yes_no("是否继续下一步？(y/n): ", default=True):
                        print("设置指南已停止。")
                        return False
                    all_passed = False
                else:
                    print(f"✅ {step['name']} 通过")
                
                if i < len(self.setup_steps):
                    self._wait_for_enter("按回车键继续下一步...")
                    
            except KeyboardInterrupt:
                print("\n\n⏹️ 设置指南被用户停止")
                return False
            except Exception as e:
                print(f"❌ {step['name']} 过程中出现错误: {e}")
                all_passed = False
        
        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 恭喜！所有设置检查都通过了！")
            print("💡 现在您可以运行程序了：")
            print("   python run.py")
        else:
            print("⚠️ 部分检查未通过，但程序可能仍然可用")
            print("💡 建议先解决上述问题，然后重新运行此指南")
        print(f"{'='*60}")
        
        return all_passed
    
    def check_environment(self):
        """检查运行环境"""
        print("\n🔍 检查运行环境...")
        
        # 检查Python版本
        version = sys.version_info
        if version < (3, 7):
            print(f"❌ Python版本过低: {version.major}.{version.minor}")
            print("💡 请升级到Python 3.7或更高版本")
            return False
        
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        
        # 检查依赖包
        required_packages = [
            ('face_recognition', '人脸识别'),
            ('PIL', '图像处理'),
            ('numpy', '数值计算'),
            ('tqdm', '进度条')
        ]
        
        missing_packages = []
        for package, description in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} ({description}) - 已安装")
            except ImportError:
                print(f"❌ {package} ({description}) - 未安装")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n💡 安装缺失的包：")
            print("   pip install -r requirements.txt")
            print("   或者单独安装:")
            for pkg in missing_packages:
                print(f"   pip install {pkg}")
            return False
        
        print("\n✅ 运行环境检查通过")
        return True
    
    def check_directories(self):
        """检查文件夹结构"""
        print("\n📁 检查文件夹结构...")
        
        required_dirs = [
            ('input', '输入数据文件夹'),
            ('input/student_photos', '学生照片文件夹'),
            ('input/class_photos', '课堂照片文件夹'),
            ('output', '输出文件夹'),
            ('src', '程序源码文件夹')
        ]
        
        all_exist = True
        
        for dir_path, description in required_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                print(f"✅ {dir_path} ({description}) - 存在")
            else:
                print(f"❌ {dir_path} ({description}) - 不存在")
                
                # 尝试创建文件夹
                if description != '程序源码文件夹':  # 不自动创建src
                    if self._prompt_yes_no(f"是否创建 {dir_path} 文件夹？(y/n): "):
                        try:
                            os.makedirs(dir_path, exist_ok=True)
                            print(f"✅ 成功创建文件夹: {dir_path}")
                        except Exception as e:
                            print(f"❌ 创建文件夹失败: {e}")
                            all_exist = False
                    else:
                        print("💡 创建文件夹后请重新运行此检查")
                        all_exist = False
                else:
                    print("💡 请确保程序文件完整")
                    all_exist = False
        
        return all_exist
    
    def check_student_photos(self):
        """检查学生照片"""
        print("\n👥 检查学生照片...")
        
        student_photos_dir = 'input/student_photos'
        
        if not os.path.exists(student_photos_dir):
            print(f"❌ 学生照片文件夹不存在: {student_photos_dir}")
            return False
        
        # 列出所有照片文件
        from .input_validator import validator
        photo_files = []
        
        for file in os.listdir(student_photos_dir):
            file_path = os.path.join(student_photos_dir, file)
            if os.path.isfile(file_path):
                ext = Path(file).suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    photo_files.append(file)
        
        if not photo_files:
            print("❌ 学生照片文件夹中没有找到照片文件")
            print("\n💡 请将学生照片放入文件夹，并按照以下格式命名:")
            print("   • Alice.jpg")
            print("   • Bob_1.jpg")
            print("   • 张三.jpg 或 张三_1.jpg")
            print("\n📸 照片要求:")
            print("   • 清晰的人脸照片")
            print("   • 使用真实姓名")
            print("   • 姓名_序号.扩展名格式")
            return False
        
        print(f"✅ 找到 {len(photo_files)} 张照片文件")
        
        # 检查文件名格式
        valid_photos = []
        invalid_photos = []
        
        for photo_file in photo_files:
            validation = validator.validate_photo_name(photo_file)
            if validation['valid']:
                valid_photos.append(validation)
            else:
                invalid_photos.append(photo_file)
        if invalid_photos:
            print(f"❌ {len(invalid_photos)} 张照片文件名格式不正确:")
            for photo in invalid_photos[:3]:
                print(f"   • {photo}")
            if len(invalid_photos) > 3:
                print(f"   ... 还有 {len(invalid_photos)-3} 张")
            
            print("\n💡 正确的命名格式:")
            print("   • Alice.jpg 或 Alice_1.jpg")
            print("   • 张三.jpg 或 张三_1.png")
            if self._prompt_yes_no("\n🔄 是否显示详细的重命名指导？(y/n): ", default=False):
                self.show_rename_guide()
            
            return False
        
        # 统计学生数量
        students = set()
        for photo in valid_photos:
            students.add(photo['name'])
        
        print(f"✅ {len(valid_photos)} 张照片命名格式正确")
        print(f"✅ 涉及 {len(students)} 名学生")
        print(f"📋 学生名单: {', '.join(list(students)[:5])}{'...' if len(students) > 5 else ''}")
        
        return True
    
    def check_class_photos(self):
        """检查课堂照片"""
        print("\n📸 检查课堂照片...")
        
        class_photos_dir = 'input/class_photos'
        
        if not os.path.exists(class_photos_dir):
            print(f"⚠️ 课堂照片文件夹不存在: {class_photos_dir}")
            
            if self._prompt_yes_no("是否创建课堂照片文件夹？(y/n): "):
                try:
                    os.makedirs(class_photos_dir, exist_ok=True)
                    print(f"✅ 成功创建文件夹: {class_photos_dir}")
                    print("💡 请将待整理的课堂照片放入此文件夹")
                    return True
                except Exception as e:
                    print(f"❌ 创建文件夹失败: {e}")
                    return False
            else:
                print("💡 创建课堂照片文件夹后，请重新运行此检查")
                return False
        
        # 检查文件夹中是否有照片
        photo_files = []
        for root, _, files in os.walk(class_photos_dir):
            for file in files:
                file_path = os.path.join(root, file)
                ext = Path(file).suffix.lower()
                if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    photo_files.append(file_path)
        
        if not photo_files:
            print("⚠️ 课堂照片文件夹为空")
            print("💡 请将待整理的课堂照片放入按日期命名的子文件夹，例如 input/class_photos/2025-12-08/")
            return True  # 不是致命错误
        
        print(f"✅ 找到 {len(photo_files)} 张课堂照片")
        print("💡 程序将根据这些照片中的人脸自动整理到对应学生的文件夹")
        
        return True
    
    def check_configuration(self):
        """检查配置文件"""
        print("\n⚙️ 检查配置文件...")
        
        config_file = 'config.json'
        
        if not os.path.exists(config_file):
            print("⚠️ 配置文件不存在")
            print("💡 程序将使用默认配置，这通常足够使用")
            
            if self._prompt_yes_no("是否创建默认配置文件？(y/n): "):
                self.create_default_config()
        
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print("✅ 配置文件格式正确")
            
            # 显示主要配置项
            if 'tolerance' in config:
                print(f"   识别阈值: {config['tolerance']}")
            if 'input_dir' in config:
                print(f"   输入数据目录: {config['input_dir']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 配置文件格式错误: {e}")
            print("💡 请检查JSON格式或删除文件使用默认配置")
            return False
    
    def create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "input_dir": DEFAULT_INPUT_DIR,
            "output_dir": DEFAULT_OUTPUT_DIR,
            "log_dir": DEFAULT_LOG_DIR,
            "tolerance": DEFAULT_TOLERANCE,
            "max_workers": 4,
            "create_subfolders": True
        }
        
        try:
            import json
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print("✅ 默认配置文件创建成功")
        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")
    
    def show_rename_guide(self):
        """显示重命名指导"""
        print("""
📸 照片重命名详细指导

🎯 目标：将照片文件名改为 姓名_序号.扩展名 格式

📋 操作步骤：

🖥️ Windows系统：
   1. 打开文件资源管理器
   2. 找到学生照片文件
   3. 右键点击文件 → 选择"重命名"
   4. 输入新名称（如：张三_1.jpg）
   5. 按回车键确认

🍎 Mac系统：
   1. 打开Finder
   2. 找到学生照片文件
   3. 单击文件选中它
   4. 按回车键
   5. 输入新名称
   6. 按回车键确认

📝 命名示例：
   ✅ 正确格式：
      • 张三_1.jpg
      • 李四_1.png
      • 王五_2.jpg
   
   ❌ 错误格式：
      • 张三.jpg (缺少序号)
      • zhangsan_1.jpg (英文名)
      • 张三_01.jpg (序号前导零)
      • 张三_1.JPG (大写扩展名)

💡 批量重命名技巧：
   • 一次重命名一个文件，避免混淆
   • 备份原文件以防出错
   • 使用数字序号区分同一学生的多张照片

⚠️ 注意事项：
   • 使用学生真实姓名
   • 名字和序号之间用下划线连接
   • 序号从1开始，不要用0
   • 扩展名使用小写
        """)

    def get_operation_guide(self, guide_type: str) -> str:
        """获取操作指南内容

        参数：
            guide_type：指南类型，可选 photo_preparation / file_organization / troubleshooting。

        返回：
            指南内容字符串。
        """
        return show_operation_guide(guide_type)


def show_help_menu():
    """显示帮助菜单"""
    print("""
🏫 主日学课堂照片整理工具 - 帮助菜单
   1. 🎯 运行设置指南
   2. 📸 查看照片准备指南
   3. 📁 查看文件组织指南
   4. 🔧 查看问题解决指南
   5. 🚀 直接运行程序
   6. ❌ 退出

💡 输入选项数字并按回车键选择
    """)
    
    while True:
        try:
            choice = input("请选择 (1-6): ").strip()
            
            if choice == '1':
                guide = InteractiveGuide()
                guide.start_setup_guide()
                break
            elif choice == '2':
                print(show_operation_guide('photo_preparation'))
                break
            elif choice == '3':
                print(show_operation_guide('file_organization'))
                break
            elif choice == '4':
                print(show_operation_guide('troubleshooting'))
                break
            elif choice == '5':
                return True  # 运行程序
            elif choice == '6':
                print("👋 再见！")
                return False  # 退出
            else:
                print("❌ 无效选项，请输入1-6之间的数字")
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            return False
        except:
            print("❌ 输入错误，请重试")
    
def show_operation_guide(guide_type):
    """显示操作指南"""
    guides = {
        'photo_preparation': """
📸 学生照片准备详细指南

🎯 目标：准备高质量的学生参考照片用于人脸识别

📋 照片质量要求：
   • 📐 分辨率：至少800x600像素
   • 📊 文件大小：1-10MB为宜
   • 🎨 格式：优先.jpg，也可以.png
   • 🖼️ 清晰度：人脸清晰，五官可见
   • 💡 光线：光线充足，避免过暗或过曝

👤 人脸要求：
   • ✅ 完整正面人脸
   • ✅ 表情自然
   • ✅ 眼睛睁开
   • ✅ 无严重遮挡
   • ✅ 背景简洁

🚫 避免问题：
   • 🚫 多人合照
   • 🚫 侧脸或背影
   • 🚫 戴口罩、帽子等遮挡物
   • 🚫 表情夸张
   • 🚫 模糊或低质量照片

📝 文件命名：
   • 格式：姓名_序号.扩展名
   • 示例：张三_1.jpg, 李四_2.png
   • 要求：中文名字，序号从1开始
   • 注意：名字和序号之间用下划线连接

💡 最佳实践：
   • 每个学生准备2-3张不同角度的照片
   • 包含正面和轻微侧面照片
   • 确保照片日期较新，容貌变化不大
   • 在相同光照条件下拍摄学生照片和课堂照片

🔄 照片获取方法：
   • 使用手机或相机拍摄
   • 扫描现有纸质照片
   • 从其他设备转移数字照片
""",
        
        'file_organization': """
📁 文件夹组织详细指南

🏗️ 标准项目结构：
sunday-photos/
├── 📂 input/                     # 输入数据主文件夹
│   ├── 📂 student_photos/        # 学生参考照片
│   │   ├── 张三.jpg
│   │   ├── 张三_2.jpg
│   │   ├── LiSi.jpg
│   │   └── 王五_1.jpg
│   └── 📂 class_photos/          # 待整理的课堂照片（建议按日期子目录）
│       ├── 2024-12-21/活动.jpg
│       ├── 2024-12-21/合照.jpg
│       └── 2024-12-28/...
├── 📂 output/                    # 整理后的输出（学生/日期分层）
├── 📂 src/                       # 程序源码
├── 📂 logs/                      # 运行日志
├── 📄 config.json               # 配置文件
└── 📄 run.py                    # 启动程序

📂 具体操作步骤：

步骤1：创建输入数据文件夹
    • 如果没有input文件夹，请创建
    • 这个文件夹将包含所有输入数据

步骤2：创建学生照片文件夹
    • 在input内创建student_photos文件夹
    • 将所有学生参考照片放入此文件夹
    • 确保文件名格式正确：姓名 或 姓名_序号.jpg

步骤3：创建课堂照片文件夹
    • 在input内创建class_photos文件夹
    • 建议按日期创建子目录，如 2024-12-21/
    • 将待整理的课堂照片放入对应日期的子目录

步骤4：创建输出文件夹
    • 创建output文件夹
    • 整理后的照片将先按学生分文件夹，再按日期分子目录存放

💡 重要提醒：
   • 文件夹名称必须完全准确
   • 注意大小写敏感性
   • 确保所有照片都在正确位置
   • 避免在文件夹名中使用空格或特殊字符

🔍 检查方法：
   • 确认每个文件夹都存在
   • 检查照片文件是否在正确文件夹
   • 验证文件名格式是否正确
""",
        
        'troubleshooting': """
🔧 问题解决详细指南

❓ 常见问题及解决方案：

🔍 问题1：程序提示"找不到文件"
可能原因：
   • 在错误的文件夹运行程序
   • 文件夹名称拼写错误
   • 文件夹不存在

解决方案：
   1️⃣ 确认当前位置：
      • 在命令行中输入：dir (Windows) 或 ls (Mac)
      • 确认能看到README.md和run.py文件
   
   2️⃣ 检查文件夹结构：
      • 确认存在input文件夹
      • 确认存在input/student_photos文件夹
   
   3️⃣ 检查文件名：
      • 确保文件夹名拼写完全正确
      • 注意大小写敏感性

👤 问题2：人脸识别不准确或失败
可能原因：
   • 照片质量不佳
   • 光线条件不好
   • 人脸不清晰
   • 识别阈值设置不当

解决方案：
   1️⃣ 改善照片质量：
      • 使用更高清晰度的照片
      • 确保光线充足
      • 避免模糊或过曝
   
   2️⃣ 调整识别阈值：
      • 降低阈值：--tolerance 0.4 (更严格)
      • 提高阈值：--tolerance 0.8 (更宽松)
      • 推荐值：0.6 (标准设置)
   
   3️⃣ 准备更多参考照片：
      • 每个学生2-3张不同角度照片
      • 包含正面和侧面照片

🚫 问题3：权限被拒绝
可能原因：
   • 文件正在被其他程序使用
   • 文件夹权限设置
   • 系统安全限制

解决方案：
   1️⃣ 关闭冲突程序：
      • 关闭可能打开照片的程序
      • 关闭文件资源管理器预览
   
   2️⃣ 检查权限：
      • 右键文件夹 → 属性 → 安全
      • 确保有读写权限
   
   3️⃣ 以管理员身份运行：
      • 右键命令提示符 → "以管理员身份运行"

💾 问题4：内存不足
可能原因：
   • 照片文件过大
   • 一次处理照片过多
   • 电脑内存不足

解决方案：
   1️⃣ 优化照片文件：
      • 压缩照片大小
      • 降低分辨率
   
   2️⃣ 分批处理：
      • 减少一次处理的照片数量
      • 分多次运行程序
   
   3️⃣ 释放系统内存：
      • 关闭其他程序
      • 重启电脑

📞 获取额外帮助：
   💡 联系前请准备：
   • 错误信息的完整截图
   • 具体的操作步骤描述
   • 文件夹结构截图
   • 使用的命令和参数

   📋 有用信息：
   • 操作系统版本
   • Python版本
   • 照片文件数量和大小
   • 出现问题的具体步骤
"""
    }
    
    return guides.get(guide_type, "没有找到相关指南。")