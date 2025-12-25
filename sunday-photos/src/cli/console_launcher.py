#!/usr/bin/env python3
"""Sunday School Photo Organizer - Console Edition (Packaged Entry)

面向老师的设计目标：最少操作、最少疑惑。

Behavior overview:
- First run: prepare the work folders (input/output/logs) under a teacher-friendly "Work folder".
    - Usually: next to the executable (portable)
    - If not writable: automatically fall back to Desktop (or Home) and print the actual path
- Next runs: organize photos; open output/ when finished

Note:
- The program may move photos under class_photos/ into YYYY-MM-DD/ subfolders (normal; used for incremental processing)
"""

import sys
import os
from pathlib import Path
import json
import time
import logging
from datetime import datetime
import platform

# 添加src目录到Python路径
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import LOG_FORMAT, UNKNOWN_PHOTOS_DIR
from core.platform_paths import get_default_work_root_dir, get_program_dir
from core.utils import is_supported_nonempty_image_path


def _try_get_teacher_helper():
    """Best-effort import for friendly teacher-facing error messages."""
    try:
        from ui.teacher_helper import TeacherHelper
        return TeacherHelper()
    except Exception:
        return None

class ConsolePhotoOrganizer:
    def __init__(self):
        self._program_dir = get_program_dir()
        self.app_directory = get_default_work_root_dir()
        self.setup_complete = False
        self.teacher_helper = _try_get_teacher_helper()
        self.logger = logging.getLogger(__name__)

        # Packaged console app: always write a UTF-8 log file under work folder.
        # Do NOT add extra console logging here to keep teacher-facing output stable.
        self._ensure_file_logging()

    def _ensure_file_logging(self) -> None:
        """Best-effort configure root logger to write logs/xxx.log.

        Keep it file-only to avoid changing console output and tests.
        """
        try:
            log_dir = self.app_directory / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            root_logger = logging.getLogger()
            if root_logger.level == logging.NOTSET:
                root_logger.setLevel(logging.INFO)

            # Avoid adding duplicate file handlers.
            for handler in root_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    return

            log_file = log_dir / f"photo_organizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            root_logger.addHandler(file_handler)
        except Exception:
            # Logging must never block teacher usage.
            return

    def _print_divider(self):
        print("=" * 56)

    def _print_section(self, title: str):
        print()
        print(f"【{title}】")

    def _print_tip(self, text: str):
        print(f"提示：{text}")

    def _print_ok(self, text: str):
        print(f"[OK] {text}")

    def _print_warn(self, text: str):
        print(f"[注意] {text}")

    def _print_next(self, text: str):
        print(f"下一步：{text}")
        
    def print_header(self):
        """打印欢迎信息"""
        # Best-effort: make Windows console output UTF-8 friendly.
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # 兼容测试中对欢迎信息的检查：保留该关键字符串
        print("主日学课堂照片自动整理工具")
        self._print_divider()
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        print("这是一款给老师用的‘零门槛’整理工具：按提示放照片，然后运行即可。")
        print(f"本次运行编号：{run_id}")
        print(f"Work folder: {self.app_directory}")
        # Teacher-friendly: don't require understanding filesystem permissions.
        override = os.environ.get("SUNDAY_PHOTOS_WORK_DIR", "").strip()
        if override:
            self._print_tip("已使用自定义工作目录（由环境变量指定）。")
        elif self.app_directory != self._program_dir:
            self._print_warn("当前程序所在位置无法创建工作文件夹，我已自动改用其它位置继续运行。")
            self._print_tip("你无需处理权限问题；按上面 Work folder 提示的路径放照片即可。")
        else:
            self._print_tip("默认使用程序所在目录；如果该位置无法创建文件夹，会自动改用桌面或主目录。")
        self._print_tip("隐私说明：照片只在本机处理，不会自动上传到网络。")
        self._print_tip("安全说明：程序不会删除照片；只会把结果复制到 output/。为了便于下次继续整理，课堂照片可能会被归档到 class_photos/ 里的日期子文件夹（例如 YYYY-MM-DD/）。")
        print("三步完成：")
        print(f"  ① Student reference photos: {self.app_directory / 'input' / 'student_photos'}")
        print(f"  ② Classroom photos: {self.app_directory / 'input' / 'class_photos'}")
        print("  ③ 再运行一次（我会自动把结果放到 output/ 并尝试打开）")
        self._print_divider()
    
    def setup_directories(self):
        """自动创建目录结构"""
        self._print_section("准备工作")
        print("正在检查并准备需要的文件夹...")
        
        directories = [
            self.app_directory,
            self.app_directory / "input",
            self.app_directory / "input" / "student_photos",
            self.app_directory / "input" / "class_photos",
            self.app_directory / "output",
            self.app_directory / "logs",
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
                                        """Student reference photos
Put reference photos under ONE folder per student:

    student_photos/Alice/
    student_photos/Bob/

Filenames can be anything.
Up to 5 reference photos per student will be used (if more than 5, the newest 5 by modified time will be used).
"""
                )
            elif directory.name == "class_photos":
                self._ensure_instruction_file(
                    directory,
                                        """Classroom photos
Put classroom/group photos here.

You may optionally organize by date folders, e.g.:
    class_photos/2025-12-21/group_photo.jpg

Supported formats: .jpg / .jpeg / .png
"""
                )
        
        if created_count > 0:
            self._print_ok(f"文件夹已准备好（新建 {created_count} 个）")
        else:
            self._print_ok("文件夹已准备好")
        return True

    def _ensure_instruction_file(self, directory, content):
        """为老师自动生成说明文件"""
        info_file = directory / "说明.txt"
        if not info_file.exists():
            info_file.write_text(content, encoding='utf-8')
    
    def _try_open_folder(self, folder_path: Path, description: str = "文件夹") -> bool:
        """尝试打开文件夹（跨平台；静默失败）。"""
        try:
            import subprocess
            
            if platform.system() == "Darwin":  # macOS
                subprocess.run(['open', str(folder_path)], check=False)
            elif platform.system() == "Windows":
                try:
                    os.startfile(str(folder_path))  # type: ignore[attr-defined]
                except Exception:
                    subprocess.run(['explorer', str(folder_path)], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', str(folder_path)], check=False)
            
            self.logger.debug(f"成功打开{description}: {folder_path}")
            return True
        except Exception as e:
            self.logger.debug(f"打开{description}失败（非关键）: {e}")
            return False
    
    def check_photos(self):
        """检查照片文件"""
        self._print_section("检查照片")
        print("我来看看照片是否已经放好...")
        self._print_tip("支持格式：JPG / JPEG / PNG")
        
        student_photos_dir = self.app_directory / "input" / "student_photos"
        class_photos_dir = self.app_directory / "input" / "class_photos"
        
        # Student reference photos: folder-only layout, so scan recursively
        student_photos = [
            p
            for p in student_photos_dir.rglob("*")
            if is_supported_nonempty_image_path(p)
        ]
        
        # Classroom photos (allow directly under class_photos or under date subfolders)
        class_photos = [
            p
            for p in class_photos_dir.rglob("*")
            if is_supported_nonempty_image_path(p)
        ]
        
        print(f"已找到：学生参考照 {len(student_photos)} 张；课堂照片 {len(class_photos)} 张")
        
        if len(student_photos) == 0:
            self._print_warn("还没有找到学生参考照。")
            self._print_next("Create one folder per student under the folder below, then put clear face photos inside")
            print(f"  {student_photos_dir}")
            self._print_tip("Example: student_photos/Alice/ref_01.jpg (filenames can be anything)")
            return False
        
        if len(class_photos) == 0:
            self._print_warn("还没有找到课堂照片。")
            self._print_next("把需要整理的课堂照片放进下面这个文件夹")
            print(f"  {class_photos_dir}")
            return False

        self._print_ok("照片已就绪，可以开始整理。")
        return True
    
    def create_config_file(self):
        """创建配置文件（如已存在则不覆盖），保证默认设置即可运行。"""
        config_data = {
            "input_dir": str(self.app_directory / "input"),
            "output_dir": str(self.app_directory / "output"),
            "log_dir": str(self.app_directory / "logs"),
            # 与 src/core/config_loader.py 读取口径保持一致（顶层字段）。
            "tolerance": 0.6,
            "min_face_size": 50,
            "parallel_recognition": {
                "enabled": False,
                "workers": 4,
                "chunk_size": 12,
                "min_photos": 30
            },
            "unknown_face_clustering": {
                "enabled": True,
                "threshold": 0.45,
                "min_cluster_size": 2
            }
        }
        
        config_file = self.app_directory / "config.json"
        if config_file.exists():
            return config_file, False

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        return config_file, True

    def _format_friendly_error(self, e: Exception, context: str = "") -> str:
        if self.teacher_helper is None:
            return f"❌ 处理过程中出现错误: {e}\n📍 {context}" if context else f"❌ 处理过程中出现错误: {e}"
        return self.teacher_helper.get_friendly_error(e, context=context)
    
    def process_photos(self):
        """处理照片"""
        self._print_section("开始整理")
        print("整理过程中请不要关闭窗口；完成后我会告诉你结果在哪。")
        self._print_tip(f"如果中途出现问题：日志会保存在 {self.app_directory / 'logs'}")
        self._print_tip("无需任何配置文件，我会自动为你准备默认配置。")
        
        start_time = time.time()
        
        try:
            # 导入处理模块
            from main import SimplePhotoOrganizer
            from config_loader import ConfigLoader
            
            # 创建/读取配置文件（存在则不覆盖；老师无需调参）
            config_file, created = self.create_config_file()
            if created:
                self._print_ok("已自动生成默认配置（无需修改）")
            else:
                self._print_tip("检测到已有配置，将直接使用。")

            config_loader = ConfigLoader(str(config_file))
            
            organizer = SimplePhotoOrganizer(
                input_dir=str(self.app_directory / "input"),
                output_dir=str(self.app_directory / "output"),
                log_dir=str(self.app_directory / "logs"),
                config_file=str(config_file),
            )
            
            if not organizer.initialize():
                raise RuntimeError("系统初始化失败，请检查日志文件")

            self._print_ok("AI 识别引擎已就绪")
            
            tolerance = config_loader.get_tolerance()
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                organizer.face_recognizer.tolerance = tolerance

            min_face_size = config_loader.get_min_face_size()
            if hasattr(organizer, 'face_recognizer') and organizer.face_recognizer:
                organizer.face_recognizer.min_face_size = min_face_size
            
            print("第 1/4 步：读取学生参考照（建立识别资料库）...")
            print("第 2/4 步：分析课堂照片（检测人脸 → 匹配姓名 → 分类保存）...")
            print("第 3/4 步：保存结果并写入报告...")
            print("第 4/4 步：尝试为你打开结果文件夹...")
            self._print_tip("处理中请耐心等待；窗口看起来‘没动’也可能正在忙碌。")
            
            # 运行完整流程
            success = organizer.run()
            elapsed_time = time.time() - start_time
            
            if not success:
                self._print_warn("整理没有完成。")
                self._print_next(f"先打开日志看看原因：{self.app_directory / 'logs'}")
                return False
            
            report = organizer.last_run_report or {}
            organize_stats = report.get('organize_stats', {})
            pipeline_stats = report.get('pipeline_stats', {})
            print("第 3/3 步：整理结果并生成统计...")
            self._print_ok("整理完成。")
            
            # 显示详细结果
            self.display_results(organize_stats, elapsed_time, pipeline_stats)
            
            # 显示文件位置
            output_dir = self.app_directory / "output"
            print(f"结果文件夹：{output_dir}")
            self._print_tip("If you see unknown_photos/, those are unrecognized photos; adding 2–3 clearer reference photos usually helps.")
            
            # 自动打开结果文件夹
            print("我来帮你打开结果文件夹...")
            if self._try_open_folder(output_dir, "结果文件夹"):
                self._print_ok("已打开结果文件夹。")
            else:
                self._print_warn("我没能自动打开文件夹（不影响结果）。")
                self._print_next("请手动打开这个文件夹查看结果")
                print(f"  {output_dir}")

            return True
            
        except Exception as e:
            context = ""
            self.logger.exception("控制台启动器主流程失败")
            try:
                context = f"工作目录：{self.app_directory}；日志目录：{self.app_directory / 'logs'}"
            except Exception:
                pass

            print("\n")
            self._print_divider()
            print("[错误] 程序遇到问题（不用紧张）")
            self._print_divider()
            print(self._format_friendly_error(e, context=context))
            print("\n你可以按下面顺序检查：")
            print("  1) 确认 student_photos/ 与 class_photos/ 里都放了照片")
            print("  2) Reference photos: put them in student_photos/<student_name>/ (folder); filenames can be anything")
            print("  3) 识别不准：给该学生补 2-3 张更清晰的正脸参考照")
            print(f"  4) 需要求助：把 logs 里最新日志发给同工/技术支持：{self.app_directory / 'logs'}")
            return False
    
    def display_results(self, results, elapsed_time, pipeline_stats=None):
        """显示处理结果"""
        pipeline_stats = pipeline_stats or {}
        total_from_pipeline = pipeline_stats.get('total_photos', results.get('total', 0))
        self._print_section("结果小结")
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
        
        print("照片已按学生姓名分类保存到 output/。")
    
    def run_auto(self):
        """自动运行模式"""
        self.print_header()
        
        # 设置文件夹
        if not self.setup_directories():
            return False
        
        # 检查照片
        if not self.check_photos():
            print()
            self._print_next("把照片放到上面提示的位置，然后再运行一次")
            print(f"桌面文件夹：{self.app_directory}")
            return False
        
        # 处理照片
        success = self.process_photos()
        
        if success:
            print()
            self._print_ok("完成。")
            self._print_next("下次只要把新课堂照片放进 class_photos/，再运行一次即可")
        else:
            print()
            self._print_warn("未完成，请按上面的提示检查后重试。")
        
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
        print("\n\n[停止] 程序已被你中断")
        return False
    except Exception as e:
        print(f"\n[错误] 程序启动失败: {e}")
        print("按回车键退出...")
        input()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)