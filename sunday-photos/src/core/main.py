"""
主程序入口
主日学课堂照片自动整理工具

管线概览（四步）：
1) 初始化组件（学生管理、人脸识别、文件组织）；
2) 扫描输入目录并按日期归档课堂照片；
3) 执行人脸识别，区分成功/未匹配/无人脸/错误；
4) 将照片按“学生/日期”写入输出目录并生成报告。
"""

import os
import sys
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import shutil

from .utils import setup_logger, is_supported_image_file, is_supported_nonempty_image_path, get_photo_date, ensure_directory_exists
from .config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR, DEFAULT_TOLERANCE, CLASS_PHOTOS_DIR, STUDENT_PHOTOS_DIR, MIN_FACE_SIZE
from .config_loader import ConfigLoader
from .incremental_state import (
    build_class_photos_snapshot,
    compute_incremental_plan,
    load_snapshot,
    save_snapshot,
)

from .recognition_cache import (
    CacheKey,
    compute_params_fingerprint,
    load_date_cache,
    normalize_cache_for_fingerprint,
    lookup_result,
    store_result,
    prune_entries,
    save_date_cache_atomic,
    invalidate_date_cache,
)
from .parallel_recognizer import parallel_recognize


class SimplePhotoOrganizer:
    """照片整理器主类（文件夹模式，简化版入口兼容）"""

    def __init__(self, input_dir=None, output_dir=None, log_dir=None, classroom_dir=None):
        """初始化照片整理器

        :param input_dir: 输入数据目录
        :param output_dir: 输出照片目录
        :param log_dir: 日志目录路径，用于存储运行日志
        """
        if input_dir is None:
            input_dir = DEFAULT_INPUT_DIR
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        if log_dir is None:
            log_dir = DEFAULT_LOG_DIR
            
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.classroom_dir = Path(classroom_dir) if classroom_dir else None
        
        # 输入照片目录：input/class_photos（保持兼容旧路径名称）
        self.photos_dir = self.input_dir / CLASS_PHOTOS_DIR

        # 自动创建教师常用的基础目录，避免手工建目录
        ensure_directory_exists(self.input_dir)
        ensure_directory_exists(self.photos_dir)
        ensure_directory_exists(self.input_dir / STUDENT_PHOTOS_DIR)
        ensure_directory_exists(self.output_dir)
        ensure_directory_exists(self.log_dir)

        # 设置日志（启用彩色控制台）
        self.logger = setup_logger(self.log_dir, enable_color_console=True)

        # 初始化各模块
        self.student_manager = None
        self.face_recognizer = None
        self.file_organizer = None

        self.initialized = False
        self.last_run_report = None
        self._incremental_plan = None
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
            # 延迟导入重型依赖，减少冷启动开销
            from .student_manager import StudentManager
            from .face_recognizer import FaceRecognizer
            from .file_organizer import FileOrganizer
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
            if is_supported_nonempty_image_path(file):
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
        """扫描输入目录，返回“本次需要处理”的课堂照片列表。

        关键点：
        - 会先把课堂照片根目录按日期归档到 YYYY-MM-DD 子目录（见 _organize_input_by_date）
        - 使用增量快照（隐藏状态）只处理新增/变更的日期目录
        - 0 字节图片会被忽略，避免产生无意义的识别异常与增量误报
        """
        self._organize_input_by_date()
        self.logger.info(f"[步骤 2/4] 正在扫描输入目录: {self.photos_dir}")

        if not self.photos_dir.exists():
            self.logger.error(f"输入目录不存在: {self.photos_dir}")
            return []

        previous = load_snapshot(self.output_dir)
        current = build_class_photos_snapshot(self.photos_dir)
        plan = compute_incremental_plan(previous, current)
        self._incremental_plan = plan

        if previous is None:
            self.logger.info("✓ 未找到增量快照（首次运行），将处理全部日期文件夹")

        if plan.deleted_dates:
            deleted_line = ", ".join(sorted(plan.deleted_dates))
            self.logger.info(f"✓ 检测到已删除的日期文件夹，将同步清理输出: {deleted_line}")

        if plan.changed_dates:
            changed_line = ", ".join(sorted(plan.changed_dates))
            self.logger.info(f"✓ 检测到有变更的日期文件夹，将仅处理这些日期: {changed_line}")
        else:
            self.logger.info("✓ 未检测到新增或变更的日期文件夹")

        photo_files = []
        for date in sorted(plan.changed_dates):
            date_dir = self.photos_dir / date
            if not date_dir.exists():
                continue
            for root, _, files in os.walk(date_dir):
                for file in files:
                    p = Path(root) / file
                    if is_supported_nonempty_image_path(p):
                        photo_files.append(str(p))

        self.logger.info(f"✓ 本次需要处理 {len(photo_files)} 张照片")
        self.stats['total_photos'] = len(photo_files)
        return photo_files

    def _cleanup_output_for_dates(self, dates):
        """清理输出目录中指定日期的数据（用于增量重建/删除同步）。

        约定：
        - 输出目录结构通常为：output/<学生名>/<日期>/... 以及 output/unknown/<日期>/...
        - 对于 deleted_dates：输入端日期文件夹被删除时，这里会同步删除输出端同日期目录
        - 对于 changed_dates：会先清理旧结果再重建，避免混入历史残留
        """
        if not dates:
            return

        for top in self.output_dir.iterdir():
            if not top.is_dir():
                continue
            for date in dates:
                date_dir = top / date
                if date_dir.exists() and date_dir.is_dir():
                    shutil.rmtree(date_dir, ignore_errors=True)

    def process_photos(self, photo_files):
        """对照片列表执行人脸识别，并按状态分类结果。

        返回：
        - recognition_results：{photo_path: [student_names]}（成功识别）
        - unknown_photos：未匹配到已知学生（但可能检测到人脸）
        - no_face_photos：未检测到人脸/人脸过小
        - error_photos：处理出错（例如损坏文件、读取失败等）
        """
        self.logger.info(f"[步骤 3/4] 正在进行人脸识别...")

        recognition_results = {}
        unknown_photos = []
        no_face_photos = []  # 记录无人脸的照片
        error_photos = []     # 记录处理出错的照片

        # 分类统计
        no_face_count = 0
        error_count = 0

        def _apply_result(photo_path: str, result: dict) -> None:
            nonlocal no_face_count, error_count

            recognized_students = result.get('recognized_students') or []
            status = result.get('status')

            if status == 'success':
                recognition_results[photo_path] = recognized_students
                self.stats['recognized_photos'] += 1
                self.stats['students_detected'].update(recognized_students)

                student_names = ", ".join(recognized_students)
                self.logger.debug(f"识别到: {os.path.basename(photo_path)} -> {student_names}")
            elif status == 'no_faces_detected':
                no_face_photos.append(photo_path)
                no_face_count += 1
                self.logger.debug(f"无人脸: {os.path.basename(photo_path)}")
            elif status == 'no_matches_found':
                unknown_photos.append(photo_path)
                self.stats['unknown_photos'] += 1
                self.logger.debug(f"未识别到已知学生: {os.path.basename(photo_path)}")
            else:
                error_photos.append(photo_path)
                error_count += 1
                msg = result.get('message', '')
                self.logger.error(f"识别出错: {os.path.basename(photo_path)} - {msg}")

            self.stats['processed_photos'] += 1

        def _extract_date_and_rel(photo_path: str) -> tuple[str, str]:
            p = Path(photo_path)
            try:
                rel = p.relative_to(self.photos_dir).as_posix()
            except Exception:
                rel = p.name
            parts = rel.split('/')
            if parts and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0] or ""):
                return parts[0], rel
            # 兜底：从路径/文件名推断日期
            return get_photo_date(photo_path), rel

        # 日期级缓存（仅对本次 changed_dates 的照片生效）
        params_fingerprint = compute_params_fingerprint(
            {
                'tolerance': float(getattr(self.face_recognizer, 'tolerance', DEFAULT_TOLERANCE)),
                'min_face_size': int(MIN_FACE_SIZE),
            }
        )
        date_to_cache = {}
        keep_rel_paths_by_date = {}
        photo_to_key = {}
        to_recognize = []
        cache_hit_count = 0

        # 使用进度条显示处理进度
        with tqdm(total=len(photo_files), desc="识别照片", unit="张") as pbar:
            # 1) 先尝试从缓存命中（命中则直接分类，不再做识别）
            for photo_path in photo_files:
                try:
                    date, rel_path = _extract_date_and_rel(photo_path)
                    st = os.stat(photo_path)
                    key = CacheKey(date=date, rel_path=rel_path, size=int(st.st_size), mtime=int(st.st_mtime))

                    if date not in date_to_cache:
                        raw_cache = load_date_cache(self.output_dir, date)
                        date_to_cache[date] = normalize_cache_for_fingerprint(raw_cache, date, params_fingerprint)
                        keep_rel_paths_by_date[date] = set()
                    keep_rel_paths_by_date[date].add(rel_path)

                    cached = lookup_result(date_to_cache[date], key)
                    if cached is not None:
                        cache_hit_count += 1
                        _apply_result(photo_path, cached)
                        pbar.update(1)
                    else:
                        to_recognize.append(photo_path)
                        photo_to_key[photo_path] = key
                except Exception as e:
                    self.logger.error(f"处理照片 {photo_path} 失败: {str(e)}")
                    error_photos.append(photo_path)
                    error_count += 1
                    self.stats['processed_photos'] += 1
                    pbar.update(1)

            # 2) 对未命中的照片做识别：满足阈值则多进程并行，否则串行
            if to_recognize:
                self.logger.info(f"✓ 识别缓存命中: {cache_hit_count} 张；待识别: {len(to_recognize)} 张")

                parallel_cfg = ConfigLoader().get_parallel_recognition()
                can_parallel = bool(parallel_cfg.get('enabled')) and len(to_recognize) >= int(parallel_cfg.get('min_photos', 0))

                if can_parallel:
                    try:
                        for photo_path, result in parallel_recognize(
                            to_recognize,
                            known_encodings=getattr(self.face_recognizer, 'known_encodings', []),
                            known_names=getattr(self.face_recognizer, 'known_student_names', []),
                            tolerance=float(getattr(self.face_recognizer, 'tolerance', DEFAULT_TOLERANCE)),
                            min_face_size=int(MIN_FACE_SIZE),
                            workers=int(parallel_cfg.get('workers', 1)),
                            chunk_size=int(parallel_cfg.get('chunk_size', 1)),
                        ):
                            _apply_result(photo_path, result)
                            key = photo_to_key.get(photo_path)
                            if key is not None:
                                store_result(date_to_cache[key.date], key, result)
                            pbar.update(1)
                    except Exception as e:
                        self.logger.warning(f"并行识别失败，将回退串行识别: {str(e)}")
                        for photo_path in to_recognize:
                            result = self.face_recognizer.recognize_faces(photo_path, return_details=True)
                            _apply_result(photo_path, result)
                            key = photo_to_key.get(photo_path)
                            if key is not None:
                                store_result(date_to_cache[key.date], key, result)
                            pbar.update(1)
                else:
                    for photo_path in to_recognize:
                        result = self.face_recognizer.recognize_faces(photo_path, return_details=True)
                        _apply_result(photo_path, result)
                        key = photo_to_key.get(photo_path)
                        if key is not None:
                            store_result(date_to_cache[key.date], key, result)
                        pbar.update(1)
            else:
                self.logger.info(f"✓ 识别缓存命中: {cache_hit_count} 张；待识别: 0 张")

        # 3) 保存/剪枝日期缓存（仅保存本次涉及到的日期）
        for date, cache in date_to_cache.items():
            try:
                prune_entries(cache, keep_rel_paths_by_date.get(date, set()))
                save_date_cache_atomic(self.output_dir, date, cache)
            except Exception:
                # 缓存失败不影响主流程
                continue

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
            # 1. 初始化系统（幂等，可重复调用 initialize）
            if not self.initialized and not self.initialize():
                return False

            # 2. 扫描输入目录（自动把散落的课堂照按日期归档到 class_photos/日期；并做增量计划）
            photo_files = self.scan_input_directory()
            plan = self._incremental_plan
            changed_dates = getattr(plan, 'changed_dates', set()) if plan else set()
            deleted_dates = getattr(plan, 'deleted_dates', set()) if plan else set()

            # 2b. 同步删除/重建：先清理输出中涉及的日期目录
            self._cleanup_output_for_dates(sorted(changed_dates | deleted_dates))

            # 2c. 删除同步：同时清理该日期的识别缓存（缓存删除失败不阻断主流程）
            for date in sorted(deleted_dates):
                invalidate_date_cache(self.output_dir, date)

            # 若本次没有任何需要处理的照片（可能是“无变化”或“仅删除”）
            if not photo_files:
                if deleted_dates:
                    self.logger.info("✓ 本次无新增/变更照片，仅执行了删除同步")
                    if plan:
                        save_snapshot(self.output_dir, plan.snapshot)
                else:
                    self.logger.info("✓ 本次无需处理：没有新增/变更/删除的日期文件夹")
                self.print_final_statistics()
                return True

            # 3. 处理照片，进行人脸识别并累积分类信息
            recognition_results, unknown_photos = self.process_photos(photo_files)

            # 4. 整理输出目录（学生/日期分层；未知放 unknown_photos/日期）
            organize_stats = self.organize_output(recognition_results, unknown_photos)

            # 4b. 成功后写入增量快照
            if plan:
                save_snapshot(self.output_dir, plan.snapshot)

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

    # 创建照片整理器实例
    organizer = SimplePhotoOrganizer(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir
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