"""
主程序入口
主日学课堂照片自动整理工具
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import shutil

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import setup_logger, is_supported_image_file, get_photo_date
from student_manager import StudentManager
from face_recognizer import FaceRecognizer
from file_organizer import FileOrganizer
from config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR, DEFAULT_TOLERANCE, CLASS_PHOTOS_DIR
from config_loader import ConfigLoader


class SimplePhotoOrganizer:
    """照片整理器主类（文件夹模式，简化版入口兼容）"""

    def __init__(self, input_dir=None, output_dir=None, log_dir=None, classroom_dir=None):
        """初始化照片整理器"""
        if input_dir is None:
            # 兼容旧的 classroom_dir 参数
            input_dir = classroom_dir if classroom_dir is not None else DEFAULT_INPUT_DIR
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        if log_dir is None:
            log_dir = DEFAULT_LOG_DIR
            
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        
        # 输入照片目录：input/class_photos（保持兼容旧路径名称）
        self.photos_dir = self.input_dir / CLASS_PHOTOS_DIR

        # 设置日志（启用彩色控制台）
        self.logger = setup_logger(self.log_dir, enable_color_console=True)

        # 初始化各模块
        self.student_manager = None
        self.face_recognizer = None
        self.file_organizer = None

        self.initialized = False
        self.last_run_report = None
        self._reset_stats()

    def _reset_stats(self):
        """重置运行统计信息"""
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_photos': 0,
            'processed_photos': 0,
            'recognized_photos': 0,
            'unknown_photos': 0,
            'students_detected': set()
        }

    def _build_run_report(self, organize_stats):
        """创建便于其他模块消费的运行报告快照"""
        pipeline_stats = dict(self.stats)
        pipeline_stats['students_detected'] = sorted(self.stats['students_detected'])
        for key in ('start_time', 'end_time'):
            if pipeline_stats[key]:
                pipeline_stats[key] = pipeline_stats[key].isoformat()

        self.last_run_report = {
            'organize_stats': organize_stats,
            'pipeline_stats': pipeline_stats
        }

    def initialize(self, force=False):
        """初始化各个组件"""
        if self.initialized and not force:
            self.logger.debug("系统组件已初始化，跳过重复初始化")
            return True
        try:
            self.logger.info("=====================================")
            self.logger.info("主日学课堂照片自动整理工具（文件夹模式）")
            self.logger.info("=====================================")

            self.logger.info("[步骤 1/4] 正在初始化系统组件...")

            # 初始化学生管理器
            self.logger.info("  - 加载学生信息...")
            self.student_manager = StudentManager(self.input_dir)

            # 检查学生参考照片
            missing_photos = self.student_manager.check_student_photos()
            if missing_photos:
                self.logger.warning(f"警告: 有 {len(missing_photos)} 名学生缺少参考照片")

            # 初始化人脸识别器
            self.logger.info("  - 初始化人脸识别器...")
            self.face_recognizer = FaceRecognizer(self.student_manager)

            # 初始化文件组织器
            self.logger.info("  - 初始化文件组织器...")
            self.file_organizer = FileOrganizer(self.output_dir)

            self.logger.info("✓ 系统组件初始化完成")
            self.initialized = True
            return True

        except Exception as e:
            self.logger.error(f"系统初始化失败: {str(e)}")
            self.initialized = False
            return False

    def _organize_input_by_date(self):
        """将上课照片根目录下的照片按日期移动到对应子目录"""
        self.logger.info("[步骤 2a/4] 正在按日期整理输入照片...")
        photo_root = Path(self.photos_dir)
        if not photo_root.exists():
            self.logger.warning(f"输入目录不存在: {photo_root}")
            return
        moved_count = 0
        for file in photo_root.iterdir():
            if file.is_file() and is_supported_image_file(file.name):
                photo_date = get_photo_date(str(file))
                date_dir = photo_root / photo_date
                date_dir.mkdir(exist_ok=True)
                target_path = date_dir / file.name
                # 避免覆盖
                if not target_path.exists():
                    shutil.move(str(file), str(target_path))
                    moved_count += 1
        if moved_count > 0:
            self.logger.info(f"✓ 已将 {moved_count} 张照片按日期移动到子目录")
        else:
            self.logger.info("✓ 输入照片已按日期整理，无需移动")

    def scan_input_directory(self):
        """扫描输入目录，获取所有照片文件"""
        self._organize_input_by_date()
        self.logger.info(f"[步骤 2/4] 正在扫描输入目录: {self.photos_dir}")

        if not self.photos_dir.exists():
            self.logger.error(f"输入目录不存在: {self.photos_dir}")
            return []

        photo_files = []

        # 遍历输入目录，获取所有照片文件
        for root, _, files in os.walk(self.photos_dir):
            for file in files:
                if is_supported_image_file(file):
                    photo_path = os.path.join(root, file)
                    photo_files.append(photo_path)

        self.logger.info(f"✓ 找到 {len(photo_files)} 张照片待处理")
        self.stats['total_photos'] = len(photo_files)

        return photo_files

    def process_photos(self, photo_files):
        """处理照片，进行人脸识别"""
        self.logger.info(f"[步骤 3/4] 正在进行人脸识别...")

        recognition_results = {}
        unknown_photos = []
        no_face_photos = []  # 新增：记录无人脸的照片
        error_photos = []     # 新增：记录处理出错的照片

        # 分类统计
        no_face_count = 0
        error_count = 0

        # 使用进度条显示处理进度
        with tqdm(total=len(photo_files), desc="识别照片", unit="张") as pbar:
            for photo_path in photo_files:
                try:
                    # 识别人脸（获取详细状态）
                    result = self.face_recognizer.recognize_faces(photo_path, return_details=True)
                    recognized_students = result['recognized_students']
                    
                    # 根据状态进行分类
                    if result['status'] == 'success':
                        recognition_results[photo_path] = recognized_students
                        self.stats['recognized_photos'] += 1
                        self.stats['students_detected'].update(recognized_students)

                        # 记录识别到的学生
                        student_names = ", ".join(recognized_students)
                        self.logger.debug(f"识别到: {os.path.basename(photo_path)} -> {student_names}")
                    elif result['status'] == 'no_faces_detected':
                        no_face_photos.append(photo_path)
                        no_face_count += 1
                        self.logger.debug(f"无人脸: {os.path.basename(photo_path)}")
                    elif result['status'] == 'no_matches_found':
                        unknown_photos.append(photo_path)
                        self.stats['unknown_photos'] += 1
                        self.logger.debug(f"未识别到已知学生: {os.path.basename(photo_path)}")
                    elif result['status'] == 'error':
                        error_photos.append(photo_path)
                        error_count += 1
                        self.logger.error(f"识别出错: {os.path.basename(photo_path)} - {result['message']}")

                    self.stats['processed_photos'] += 1

                except Exception as e:
                    self.logger.error(f"处理照片 {photo_path} 失败: {str(e)}")
                    error_photos.append(photo_path)
                    error_count += 1

                pbar.update(1)

        self.logger.info(f"✓ 人脸识别完成")
        self.logger.info(f"  - 识别到学生的照片: {self.stats['recognized_photos']} 张")
        self.logger.info(f"  - 无人脸照片: {no_face_count} 张")
        self.logger.info(f"  - 未知照片: {self.stats['unknown_photos']} 张")
        self.logger.info(f"  - 处理出错照片: {error_count} 张")
        if self.stats['students_detected']:
            students_line = ', '.join(sorted(self.stats['students_detected']))
        else:
            students_line = '暂无'
        self.logger.info(f"  - 识别到的学生: {students_line}")

        # 合并未知照片、无人脸照片和出错照片
        all_unknown_photos = unknown_photos + no_face_photos + error_photos
        return recognition_results, all_unknown_photos

    def organize_output(self, recognition_results, unknown_photos):
        """组织输出目录"""
        self.logger.info(f"[步骤 4/4] 正在整理照片...")

        # 使用文件组织器整理照片
        stats = self.file_organizer.organize_photos(
            self.photos_dir,
            recognition_results,
            unknown_photos
        )

        # 创建整理报告
        report_file = self.file_organizer.create_summary_report(stats)

        self.logger.info("✓ 照片整理完成")

        if report_file:
            self.logger.info(f"✓ 整理报告已生成: {report_file}")

        self._build_run_report(stats)
        return stats

    def run(self):
        """运行照片整理流程"""
        self._reset_stats()
        self.last_run_report = None
        self.stats['start_time'] = datetime.now()

        try:
            # 1. 初始化系统
            if not self.initialized and not self.initialize():
                return False

            # 2. 扫描输入目录
            photo_files = self.scan_input_directory()
            if not photo_files:
                self.logger.warning("输入目录中没有找到照片文件")
                return False

            # 3. 处理照片，进行人脸识别
            recognition_results, unknown_photos = self.process_photos(photo_files)

            # 4. 整理输出目录
            organize_stats = self.organize_output(recognition_results, unknown_photos)

            # 5. 输出最终统计信息
            self.print_final_statistics()

            return True

        except Exception as e:
            self.logger.error(f"照片整理过程中发生错误: {str(e)}")
            return False

        finally:
            self.stats['end_time'] = datetime.now()

    def print_final_statistics(self):
        """打印最终统计信息"""
        self.logger.info("=====================================")
        self.logger.info("处理完成！")

        # 计算总耗时
        if self.stats['start_time'] and self.stats['end_time']:
            elapsed = self.stats['end_time'] - self.stats['start_time']
            minutes, seconds = divmod(elapsed.total_seconds(), 60)
            self.logger.info(f"总耗时: {int(minutes)}分{int(seconds)}秒")

        self.logger.info(f"总照片数: {self.stats['total_photos']}")
        self.logger.info(f"成功识别: {self.stats['recognized_photos']}")
        self.logger.info(f"未知照片: {self.stats['unknown_photos']}")

        if self.stats['students_detected']:
            self.logger.info(f"识别到的学生: {', '.join(sorted(self.stats['students_detected']))}")
        else:
            self.logger.info("识别到的学生: 暂无")

        self.logger.info(f"输出目录: {os.path.abspath(self.output_dir)}")
        self.logger.info("=====================================")


def parse_arguments(config_loader=None):
    """解析命令行参数"""
    # 如果提供了配置加载器，使用配置文件中的默认值
    if config_loader:
        default_input_dir = config_loader.get_input_dir()
        default_output_dir = config_loader.get_output_dir()
        default_log_dir = config_loader.get_log_dir()
        default_tolerance = config_loader.get_tolerance()
    else:
        # 否则使用硬编码的默认值
        default_input_dir = DEFAULT_INPUT_DIR
        default_output_dir = DEFAULT_OUTPUT_DIR
        default_log_dir = DEFAULT_LOG_DIR
        default_tolerance = DEFAULT_TOLERANCE

    parser = argparse.ArgumentParser(description="主日学课堂照片自动整理工具")

    parser.add_argument(
        "--input-dir", 
        default=default_input_dir,
        help=f"输入数据目录 (默认: {default_input_dir})"
    )

    # 兼容旧参数名称
    parser.add_argument(
        "--classroom-dir", 
        dest="classroom_dir",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--output-dir", 
        default=default_output_dir,
        help=f"输出照片目录 (默认: {default_output_dir})"
    )

    parser.add_argument(
        "--log-dir", 
        default=default_log_dir,
        help=f"日志目录 (默认: {default_log_dir})"
    )

    parser.add_argument(
        "--tolerance", 
        type=float, 
        default=default_tolerance,
        help=f"人脸识别阈值 (0-1, 默认: {default_tolerance})"
    )

    return parser.parse_args()


def main():
    """主函数"""
    # 首先加载配置文件
    config_loader = ConfigLoader()
    
    # 使用配置加载器解析命令行参数
    args = parse_arguments(config_loader)

    input_dir = args.input_dir or getattr(args, "classroom_dir", None)

    # 创建照片整理器实例
    organizer = SimplePhotoOrganizer(
        input_dir=input_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        classroom_dir=getattr(args, "classroom_dir", None)
    )
    
    # 初始化系统
    if not organizer.initialize():
        sys.exit(1)
    
    # 设置人脸识别阈值
    if hasattr(organizer, 'face_recognizer'):
        organizer.face_recognizer.tolerance = args.tolerance

    # 运行整理流程
    success = organizer.run()

    # 根据结果返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()