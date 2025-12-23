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
        print("主日学照片整理工具")
        print("=" * 50)
        print(f"桌面工作文件夹：{self.app_directory}")
        print("使用方法：把照片放好 → 再运行一次")
        print("提示：课堂照片可能会被按日期移动到 YYYY-MM-DD/（正常现象）")
        print("=" * 50)
    
    def setup_directories(self):
        """自动创建目录结构"""
        print("正在检查/创建文件夹...")
        
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
                # 不逐项刷屏

            if directory.name == "student_photos":
                self._ensure_instruction_file(
                    directory,
                    """学生照片文件夹
请将学生的参考照片放在这里。

照片命名：姓名.jpg 或 姓名_序号.jpg（序号可选）
示例：张三.jpg、张三_2.jpg、LiSi.jpg

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
        
        if created_count > 0:
            print(f"文件夹已准备好（新建 {created_count} 个）")
        else:
            print("文件夹已准备好")
        return True

    def _ensure_instruction_file(self, directory, content):
        """为老师自动生成说明文件"""
        info_file = directory / "说明.txt"
        if not info_file.exists():
            info_file.write_text(content, encoding='utf-8')
    
    def check_photos(self):
        """检查照片文件"""
        print("正在检查照片...")
        
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
        
        print(f"学生参考照：{len(student_photos)} 张；课堂照片：{len(class_photos)} 张")
        
        if len(student_photos) == 0:
            print("未找到学生参考照片。")
            print("请把学生照片放这里：")
            print(f"  {student_photos_dir}")
            print("命名示例：张三.jpg 或 张三_2.jpg")
            return False
        
        if len(class_photos) == 0:
            print("未找到课堂照片。")
            print("请把课堂照片放这里：")
            print(f"  {class_photos_dir}")
            return False

        print("照片已就绪。")
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
            # 老师无需理解/修改配置；保留该文件主要用于一致性与排障。
            return config_file

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        # 不提示老师去找配置/改配置
        return config_file

    def _format_friendly_error(self, e: Exception, context: str = "") -> str:
        if self.teacher_helper is None:
            return f"❌ 处理过程中出现错误: {e}\n📍 {context}" if context else f"❌ 处理过程中出现错误: {e}"
        return self.teacher_helper.get_friendly_error(e, context=context)
    
    def process_photos(self):
        """处理照片"""
        print("开始整理，请稍候...")
        
        start_time = time.time()
        
        try:
            # 导入处理模块
            from main import SimplePhotoOrganizer
            from config_loader import ConfigLoader
            
            # 创建/读取配置文件（存在则不覆盖；主要用于一致性与排障，老师无需调参）
            config_file = self.create_config_file()
            
            config_loader = ConfigLoader(str(config_file))
            
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
            
            print("正在识别并分类（可能需要几分钟）...")
            
            # 运行完整流程
            success = organizer.run()
            elapsed_time = time.time() - start_time
            
            if not success:
                print("整理未完成。")
                print(f"日志在：{self.app_directory / 'logs'}")
                return False
            
            report = organizer.last_run_report or {}
            organize_stats = report.get('organize_stats', {})
            pipeline_stats = report.get('pipeline_stats', {})
            print("整理完成。")
            
            # 显示详细结果
            self.display_results(organize_stats, elapsed_time, pipeline_stats)
            
            # 显示文件位置
            output_dir = self.app_directory / "output"
            print(f"结果在：{output_dir}")
            
            # 询问是否打开文件夹
            try:
                import subprocess
                import platform

                print("正在打开结果文件夹...")
                
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(['open', str(output_dir)])
                elif platform.system() == "Windows":
                    subprocess.run(['explorer', str(output_dir)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(output_dir)])
                    
                print("已打开。")
                
            except Exception as e:
                print("无法自动打开，请手动打开：")
                print(f"  {output_dir}")

            return True
            
        except Exception as e:
            context = ""
            try:
                context = f"桌面目录：{self.app_directory}；日志目录：{self.app_directory / 'logs'}"
            except Exception:
                pass

            print("\n" + "=" * 50)
            print("程序遇到问题")
            print("=" * 50)
            print(self._format_friendly_error(e, context=context))
            print("\n建议：")
            print("  1) 确认 student_photos/ 与 class_photos/ 里都有照片")
            print("  2) 学生照片命名：张三.jpg 或 张三_2.jpg")
            print("  3) 识别不准：给该学生补 2-3 张清晰正脸参考照")
            print(f"  4) 需要求助：把 logs 里最新日志发给技术支持：{self.app_directory / 'logs'}")
            return False
    
    def display_results(self, results, elapsed_time, pipeline_stats=None):
        """显示处理结果"""
        pipeline_stats = pipeline_stats or {}
        total_from_pipeline = pipeline_stats.get('total_photos', results.get('total', 0))
        print("结果统计：")
        print(f"  用时：{elapsed_time:.1f} 秒")
        print(f"  总照片：{total_from_pipeline} 张")
        print(f"  已分类：{results.get('copied', 0)} 张")
        print(f"  失败：{results.get('failed', 0)} 张")
        print(f"  未识别：{pipeline_stats.get('unknown_photos', results.get('students', {}).get(UNKNOWN_PHOTOS_DIR, 0))} 张")
        
        students = results.get('students', {})
        detected_students = pipeline_stats.get('students_detected', list(students.keys()))
        print(f"  识别到学生：{len(detected_students)} 人")
        
        if students:
            print()
            # 对老师来说按学生逐条刷屏可能过长；仅保留总体统计。
        
        print("照片已按学生姓名分类保存。")
    
    def run_auto(self):
        """自动运行模式"""
        self.print_header()
        
        # 设置文件夹
        if not self.setup_directories():
            return False
        
        # 检查照片
        if not self.check_photos():
            print("\n下一步：把照片放到上面提示的位置，然后再运行一次。")
            print(f"桌面文件夹：{self.app_directory}")
            return False
        
        # 处理照片
        success = self.process_photos()
        
        if success:
            print("\n完成。下次：把新课堂照片放进 class_photos/，再运行一次即可。")
        else:
            print("\n未完成，请按提示检查后重试。")
        
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