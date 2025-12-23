#!/usr/bin/env python3
"""主日学照片整理工具 - 控制台版本（打包版入口）

面向老师的设计目标：最少操作、最少疑惑。

行为概览：
- 首次运行：在桌面创建“主日学照片整理/”目录结构并提示放照片
- 再次运行：读取配置并整理照片；完成后自动打开 output/

重要说明：
- 程序可能会把 class_photos 根目录的照片按日期移动到 YYYY-MM-DD/ 子目录（正常现象，用于增量处理）
"""

import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime

# 添加src目录到Python路径
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import UNKNOWN_PHOTOS_DIR


def _try_get_teacher_helper():
    """Best-effort import for friendly teacher-facing error messages."""
    try:
        from ui.teacher_helper import TeacherHelper
        return TeacherHelper()
    except Exception:
        return None

class ConsolePhotoOrganizer:
    def __init__(self):
        self.app_directory = Path.home() / "Desktop" / "主日学照片整理"
        self.setup_complete = False
        self.teacher_helper = _try_get_teacher_helper()
        
    def print_header(self):
        """打印欢迎信息"""
        print("🏫 主日学课堂照片自动整理工具 - 控制台版本")
        print("=" * 60)
        print("👋 欢迎使用！本工具将自动为您整理主日学课堂照片")
        print("📍 工作目录:", self.app_directory)
        print("📝 提示：程序可能会把课堂照片按日期移动到 YYYY-MM-DD/ 子目录（正常现象）")
        print("=" * 60)
        print()
    
    def setup_directories(self):
        """自动创建目录结构"""
        print("📁 正在创建文件夹结构...")
        
        directories = [
            self.app_directory,
            self.app_directory / "student_photos",
            self.app_directory / "class_photos", 
            self.app_directory / "output",
            self.app_directory / "logs"
        ]
        
        created_count = 0
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created_count += 1
                print(f"   ✅ 创建: {directory.name}")
            else:
                print(f"   ✓ 已存在: {directory.name}")

            if directory.name == "student_photos":
                self._ensure_instruction_file(
                    directory,
                    """学生照片文件夹
请将学生的参考照片放在这里。

照片命名格式：姓名_序号.jpg
示例：张三_1.jpg、李四_1.jpg

每个学生至少需要1张包含清晰人脸的照片。
"""
                )
            elif directory.name == "class_photos":
                self._ensure_instruction_file(
                    directory,
                    """课堂照片文件夹
请需要整理的课堂照片放在这里。

可以是单个人或多人的课堂照片。
程序会自动识别照片中的学生并分类。

支持格式：.jpg、.jpeg、.png
"""
                )
        
        print(f"📂 文件夹设置完成！共创建 {created_count} 个新文件夹")
        print()
        return True

    def _ensure_instruction_file(self, directory, content):
        """为老师自动生成说明文件"""
        info_file = directory / "说明.txt"
        if not info_file.exists():
            info_file.write_text(content, encoding='utf-8')
    
    def check_photos(self):
        """检查照片文件"""
        print("🔍 正在检查照片文件...")
        
        student_photos_dir = self.app_directory / "student_photos"
        class_photos_dir = self.app_directory / "class_photos"
        
        # 检查学生照片
        student_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
        student_photos = []
        for ext in student_extensions:
            student_photos.extend(student_photos_dir.glob(ext))
        
        # 检查课堂照片
        class_photos = []
        for ext in student_extensions:
            class_photos.extend(class_photos_dir.glob(ext))
        
        print(f"   📸 学生参考照片: {len(student_photos)} 张")
        if len(student_photos) > 0:
            print("   📝 示例学生照片:")
            for i, photo in enumerate(student_photos[:3]):
                print(f"      - {photo.name}")
            if len(student_photos) > 3:
                print(f"      ... 还有 {len(student_photos) - 3} 张")
        
        print(f"   📚 课堂照片: {len(class_photos)} 张")
        if len(class_photos) > 0:
            print("   📝 示例课堂照片:")
            for i, photo in enumerate(class_photos[:3]):
                print(f"      - {photo.name}")
            if len(class_photos) > 3:
                print(f"      ... 还有 {len(class_photos) - 3} 张")
        
        print()
        
        if len(student_photos) == 0:
            print("❌ 未找到学生参考照片！")
            print("💡 请将学生照片放入以下文件夹:")
            print(f"   {student_photos_dir}")
            print("📸 照片命名格式：姓名_序号.jpg（如：张三_1.jpg）")
            return False
        
        if len(class_photos) == 0:
            print("❌ 未找到课堂照片！")
            print("💡 请将课堂照片放入以下文件夹:")
            print(f"   {class_photos_dir}")
            return False
        
        print("✅ 照片检查通过！")
        return True
    
    def create_config_file(self):
        """创建配置文件（如已存在则不覆盖）。"""
        config_data = {
            "input_dir": str(self.app_directory),
            "output_dir": str(self.app_directory / "output"),
            "log_dir": str(self.app_directory / "logs"),
            "photo_processing": {
                "supported_formats": ["jpg", "jpeg", "png"]
            },
            "face_recognition": {
                "tolerance": 0.6,
                "min_face_size": 50,
                "enable_enhanced_processing": True
            }
        }
        
        config_file = self.app_directory / "config.json"
        if config_file.exists():
            print(f"⚙️ 已检测到配置文件，将沿用现有配置: {config_file}")
            print("   如需调整识别准确度，请修改：face_recognition.tolerance（默认0.6，建议0.45~0.75）")
            return config_file

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        print(f"⚙️ 配置文件已创建: {config_file}")
        print("   可选：修改 face_recognition.tolerance 调整识别准确度（默认0.6，建议0.45~0.75）")
        return config_file

    def _format_friendly_error(self, e: Exception, context: str = "") -> str:
        if self.teacher_helper is None:
            return f"❌ 处理过程中出现错误: {e}\n📍 {context}" if context else f"❌ 处理过程中出现错误: {e}"
        return self.teacher_helper.get_friendly_error(e, context=context)
    
    def process_photos(self):
        """处理照片"""
        print("🚀 开始处理照片...")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # 导入处理模块
            from main import SimplePhotoOrganizer
            from config_loader import ConfigLoader
            
            # 创建/读取配置文件（存在则不覆盖，支持老师调参）
            config_file = self.create_config_file()
            
            print("📋 加载配置...")
            config_loader = ConfigLoader(str(config_file))
            
            print("🔧 初始化处理系统...")
            organizer = SimplePhotoOrganizer(
                input_dir=str(self.app_directory),
                output_dir=str(self.app_directory / "output"),
                log_dir=str(self.app_directory / "logs")
            )
            
            if not organizer.initialize():
                raise RuntimeError("系统初始化失败，请检查日志文件")
            
            tolerance = config_loader.get_tolerance()
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                organizer.face_recognizer.tolerance = tolerance

            print(f"🎛️ 当前识别阈值 tolerance = {tolerance}")
            
            print("📸 开始识别人脸并分类照片...")
            print("   ⏳ 这可能需要几分钟时间，请耐心等待...")
            print()
            
            # 运行完整流程
            success = organizer.run()
            elapsed_time = time.time() - start_time
            
            if not success:
                print("❌ 整理任务未完成，请查看日志文件了解详情。")
                print(f"📂 日志位置: {self.app_directory / 'logs'}")
                return False
            
            report = organizer.last_run_report or {}
            organize_stats = report.get('organize_stats', {})
            pipeline_stats = report.get('pipeline_stats', {})
            print("-" * 40)
            print("🎉 照片整理完成！")
            print()
            
            # 显示详细结果
            self.display_results(organize_stats, elapsed_time, pipeline_stats)
            
            # 显示文件位置
            output_dir = self.app_directory / "output"
            print("📂 整理后的照片位置:")
            print(f"   {output_dir}")
            print()
            
            # 询问是否打开文件夹
            try:
                import subprocess
                import platform
                
                print("🔍 正在打开输出文件夹...")
                
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', str(output_dir)])
                elif platform.system() == "Windows":
                    subprocess.run(['explorer', str(output_dir)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(output_dir)])
                    
                print("✅ 文件夹已打开")
                
            except Exception as e:
                print(f"⚠️ 无法自动打开文件夹: {e}")
                print(f"📂 请手动打开: {output_dir}")

            return True
            
        except Exception as e:
            context = ""
            try:
                context = f"桌面目录：{self.app_directory}；日志目录：{self.app_directory / 'logs'}"
            except Exception:
                pass

            print("\n" + "=" * 60)
            print("😕 程序遇到了问题")
            print("=" * 60)
            print(self._format_friendly_error(e, context=context))
            print("\n💡 建议按以下顺序排查：")
            print("   1) 确认 student_photos/ 与 class_photos/ 里都有照片")
            print("   2) 学生照片命名：姓名.jpg 或 姓名_2.jpg")
            print("   3) 照片格式：jpg / jpeg / png")
            print("   4) 如识别不准：可编辑桌面目录下 config.json 调整 tolerance")
            return False
    
    def display_results(self, results, elapsed_time, pipeline_stats=None):
        """显示处理结果"""
        pipeline_stats = pipeline_stats or {}
        total_from_pipeline = pipeline_stats.get('total_photos', results.get('total', 0))
        print("📊 处理结果统计:")
        print(f"   ⏱️  处理时间: {elapsed_time:.1f} 秒")
        print(f"   📸 总照片数: {total_from_pipeline} 张")
        print(f"   ✅ 成功分类: {results.get('copied', 0)} 张")
        print(f"   ❌ 处理失败: {results.get('failed', 0)} 张")
        print(f"   ❓ 未识别: {pipeline_stats.get('unknown_photos', results.get('students', {}).get(UNKNOWN_PHOTOS_DIR, 0))} 张")
        
        students = results.get('students', {})
        detected_students = pipeline_stats.get('students_detected', list(students.keys()))
        print(f"   👥 识别到的学生: {len(detected_students)} 人")
        
        if students:
            print()
            print("📝 各学生照片统计:")
            for student_name, count in students.items():
                if student_name == UNKNOWN_PHOTOS_DIR:
                    label = "未知照片"
                else:
                    label = f"👤 {student_name}"
                print(f"   {label}: {count} 张")
        
        print()
        print("✅ 整理完成！照片已按学生姓名分类保存。")
    
    def run_auto(self):
        """自动运行模式"""
        self.print_header()
        
        # 设置文件夹
        if not self.setup_directories():
            return False
        
        # 检查照片
        if not self.check_photos():
            print()
            print("💡 使用说明:")
            print("1. 将学生参考照片放入 'student_photos' 文件夹")
            print("2. 将需要整理的课堂照片放入 'class_photos' 文件夹")
            print("3. 重新运行此程序")
            print()
            print("📂 文件夹位置:")
            print(f"   {self.app_directory}")
            return False
        
        # 处理照片
        success = self.process_photos()
        
        if success:
            print()
            print("🎊 任务完成！感谢使用主日学照片整理工具！")
            print()
            print("💡 下次使用:")
            print("   1. 添加新的课堂照片到 'class_photos' 文件夹")
            print("   2. 重新运行此程序即可")
        else:
            print()
            print("❌ 处理失败，请检查上述错误信息并重试。")
        
        return success

def main():
    """主函数"""
    try:
        organizer = ConsolePhotoOrganizer()
        success = organizer.run_auto()
        
        if not success:
            print()
            print("按回车键退出...")
            input()
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 程序已被用户停止")
        return False
    except Exception as e:
        print(f"\n❌ 程序启动失败: {e}")
        print("按回车键退出...")
        input()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)