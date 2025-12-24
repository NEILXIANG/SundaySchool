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
import warnings
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import shutil
from typing import Dict, List

# 忽略 face_recognition_models 的 pkg_resources 弃用警告
warnings.filterwarnings("ignore", category=UserWarning, module='face_recognition_models')

from .utils import (
    setup_logger,
    is_supported_image_file,
    is_supported_nonempty_image_path,
    get_photo_date,
    ensure_directory_exists,
    parse_date_from_text,
)
from .utils import is_ignored_fs_entry
from .config import DEFAULT_CONFIG, UNKNOWN_PHOTOS_DIR
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
from .clustering import UnknownClustering


class ServiceContainer:
    """
    依赖注入容器，统一管理核心服务实例。
    支持自定义mock和解耦对象创建，便于测试和扩展。
    """
    def __init__(self, config=None):
        self._services = {}
        self.config = config

    def get_student_manager(self):
        if 'student_manager' not in self._services:
            from .student_manager import StudentManager
            input_dir = self.config.get('input_dir') if self.config else None
            self._services['student_manager'] = StudentManager(input_dir)
        return self._services['student_manager']

    def get_face_recognizer(self):
        if 'face_recognizer' not in self._services:
            from .face_recognizer import FaceRecognizer
            sm = self.get_student_manager()
            tolerance = self.config.get('tolerance') if self.config else None
            min_face_size = self.config.get('min_face_size') if self.config else None
            self._services['face_recognizer'] = FaceRecognizer(sm, tolerance, min_face_size)
        return self._services['face_recognizer']

    def get_file_organizer(self):
        if 'file_organizer' not in self._services:
            from .file_organizer import FileOrganizer
            output_dir = self.config.get('output_dir') if self.config else None
            self._services['file_organizer'] = FileOrganizer(output_dir)
        return self._services['file_organizer']


class SimplePhotoOrganizer:
    """
    照片整理器主类（支持依赖注入容器）
    """
    def __init__(self, input_dir=None, output_dir=None, log_dir=None, classroom_dir=None, service_container=None, config_file=None):
        if input_dir is None:
            input_dir = DEFAULT_CONFIG['input_dir']
        if output_dir is None:
            output_dir = DEFAULT_CONFIG['output_dir']
        if log_dir is None:
            log_dir = DEFAULT_CONFIG['log_dir']
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.classroom_dir = Path(classroom_dir) if classroom_dir else None
        self.photos_dir = self.input_dir / DEFAULT_CONFIG['class_photos_dir']
        ensure_directory_exists(self.input_dir)
        ensure_directory_exists(self.photos_dir)
        ensure_directory_exists(self.input_dir / DEFAULT_CONFIG['student_photos_dir'])
        ensure_directory_exists(self.output_dir)
        ensure_directory_exists(self.log_dir)
        self.logger = setup_logger(self.log_dir, enable_color_console=True)
        self.service_container = service_container
        self._config_file = config_file
        self._config_loader = None
        self.student_manager = None
        self.face_recognizer = None
        self.file_organizer = None
        self.initialized = False
        self.last_run_report = None
        self._incremental_plan = None
        self._reset_stats()

    def _get_config_loader(self) -> ConfigLoader:
        if self._config_loader is None:
            if self._config_file:
                cfg_path = Path(self._config_file)
                # 对打包版：相对路径以 config.json 所在目录为基准
                self._config_loader = ConfigLoader(str(cfg_path), base_dir=cfg_path.parent)
            else:
                self._config_loader = ConfigLoader()
        return self._config_loader

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

            sc = self.service_container
            if sc:
                self.student_manager = sc.get_student_manager()
                self.face_recognizer = sc.get_face_recognizer()
                self.file_organizer = sc.get_file_organizer()
            else:
                from .student_manager import StudentManager
                from .face_recognizer import FaceRecognizer
                from .file_organizer import FileOrganizer
                self.student_manager = StudentManager(self.input_dir)
                # 让 min_face_size 可从 config.json 生效（未提供则回退默认值）
                cfg = self._get_config_loader()
                self.face_recognizer = FaceRecognizer(
                    self.student_manager,
                    tolerance=float(getattr(cfg, 'get_tolerance')()),
                    min_face_size=int(getattr(cfg, 'get_min_face_size')()),
                )
                self.file_organizer = FileOrganizer(self.output_dir)

            # 检查学生参考照片
            missing_photos = self.student_manager.check_student_photos()
            if missing_photos:
                self.logger.warning(f"警告: 有 {len(missing_photos)} 名学生缺少参考照片")

            self.logger.info("✓ 系统组件初始化完成")
            self.initialized = True
            return True

        except Exception as e:
            self.logger.exception(f"系统初始化失败: {str(e)}")
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

        # 兼容多种“日期文件夹写法”：输入端可为 2025.12.23 / 2025年12月23日 等。
        # 这里统一解析为 YYYY-MM-DD，用于增量计划与输出目录命名。
        date_to_dirs: Dict[str, List[Path]] = {}
        try:
            for child in self.photos_dir.iterdir():
                if is_ignored_fs_entry(child):
                    continue
                if not child.is_dir():
                    continue
                normalized = parse_date_from_text(child.name)
                if not normalized:
                    continue
                date_to_dirs.setdefault(normalized, []).append(child)

                # 兼容嵌套目录：class_photos/YYYY/MM/DD/...
                # 注意：这里的 child 已经被当作“日期目录”处理过时，不再深入。

            # 第二轮：识别嵌套 YYYY/MM/DD 结构（老师常见按年/月/日建文件夹）
            for year_dir in self.photos_dir.iterdir():
                if is_ignored_fs_entry(year_dir) or (not year_dir.is_dir()):
                    continue
                if not re.fullmatch(r"\d{4}", year_dir.name or ""):
                    continue
                for month_dir in year_dir.iterdir():
                    if is_ignored_fs_entry(month_dir) or (not month_dir.is_dir()):
                        continue
                    if not re.fullmatch(r"\d{1,2}", month_dir.name or ""):
                        continue
                    for day_dir in month_dir.iterdir():
                        if is_ignored_fs_entry(day_dir) or (not day_dir.is_dir()):
                            continue
                        if not re.fullmatch(r"\d{1,2}", day_dir.name or ""):
                            continue

                        normalized = parse_date_from_text(f"{year_dir.name}/{month_dir.name}/{day_dir.name}")
                        if not normalized:
                            continue
                        date_to_dirs.setdefault(normalized, []).append(day_dir)
        except Exception:
            date_to_dirs = {}

        photo_files = []
        for date in sorted(plan.changed_dates):
            for date_dir in sorted(date_to_dirs.get(date, []), key=lambda p: p.name):
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
            if is_ignored_fs_entry(top):
                continue
            if not top.is_dir():
                continue

            # 普通目录：output/<student>/<date>
            for date in dates:
                date_dir = top / date
                if date_dir.exists() and date_dir.is_dir():
                    shutil.rmtree(date_dir, ignore_errors=True)

            # unknown 目录：output/unknown_photos/<date> 以及 output/unknown_photos/Unknown_Person_X/<date>
            if top.name == UNKNOWN_PHOTOS_DIR:
                for date in dates:
                    date_dir = top / date
                    if date_dir.exists() and date_dir.is_dir():
                        shutil.rmtree(date_dir, ignore_errors=True)

                for cluster_dir in top.iterdir():
                    if is_ignored_fs_entry(cluster_dir):
                        continue
                    if not cluster_dir.is_dir():
                        continue
                    # 只处理 Unknown_Person_X 这类子目录
                    if not cluster_dir.name.startswith("Unknown_Person_"):
                        continue
                    for date in dates:
                        date_dir = cluster_dir / date
                        if date_dir.exists() and date_dir.is_dir():
                            shutil.rmtree(date_dir, ignore_errors=True)

    def process_photos(self, photo_files):
        """对照片列表执行人脸识别，并按状态分类结果。

        返回：
        - recognition_results：{photo_path: [student_names]}（成功识别）
        - unknown_photos：未匹配到已知学生（但可能检测到人脸）
        - no_face_photos：未检测到人脸/人脸过小
        - error_photos：处理出错（例如损坏文件、读取失败等）
        - unknown_encodings_map: {photo_path: [encodings]} (未知人脸编码)
        """
        self.logger.info(f"[步骤 3/4] 正在进行人脸识别...")

        recognition_results = {}
        unknown_photos = []
        no_face_photos = []  # 记录无人脸的照片
        error_photos = []     # 记录处理出错的照片
        unknown_encodings_map = {} # 记录未知人脸编码

        # 分类统计
        no_face_count = 0
        error_count = 0

        def _apply_result(photo_path: str, result: dict) -> None:
            nonlocal no_face_count, error_count

            recognized_students = result.get('recognized_students') or []
            status = result.get('status')
            
            # 收集未知人脸编码
            if 'unknown_encodings' in result and result['unknown_encodings']:
                unknown_encodings_map[photo_path] = result['unknown_encodings']

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
            except (ValueError, OSError) as e:
                # 照片不在 photos_dir 下或路径访问异常，使用文件名作为相对路径
                self.logger.debug(f"照片 {photo_path} 路径解析异常，使用文件名: {e}")
                rel = p.name
            parts = rel.split('/')
            if parts:
                normalized = parse_date_from_text(parts[0] or "")
                if normalized:
                    return normalized, rel
            # 兜底：从路径/文件名推断日期
            return get_photo_date(photo_path), rel

        # 日期级缓存（仅对本次 changed_dates 的照片生效）
        tolerance = float(getattr(self.face_recognizer, 'tolerance', DEFAULT_CONFIG['tolerance']))
        min_face_size = int(getattr(self.face_recognizer, 'min_face_size', DEFAULT_CONFIG['min_face_size']))
        params_fingerprint = compute_params_fingerprint(
            {
                'tolerance': tolerance,
                'min_face_size': min_face_size,
                # 参考照变化必须触发缓存失效（补/删/替换参考照应立刻生效）
                'reference_fingerprint': str(getattr(self.face_recognizer, 'reference_fingerprint', '')),
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
                    self.logger.exception(f"处理照片 {photo_path} 时发生异常")
                    error_photos.append(photo_path)
                    error_count += 1
                    self.stats['processed_photos'] += 1
                    pbar.update(1)

            # 2) 对未命中的照片做识别：智能决策并行/串行模式
            if to_recognize:
                self.logger.info(f"✓ 识别缓存命中: {cache_hit_count} 张；待识别: {len(to_recognize)} 张")

                parallel_cfg = self._get_config_loader().get_parallel_recognition()
                config_enabled = bool(parallel_cfg.get('enabled'))
                min_photos_threshold = int(parallel_cfg.get('min_photos', 30))
                photo_count = len(to_recognize)
                
                # 智能决策：根据配置、照片数量、系统资源决定是否并行
                can_parallel = config_enabled and photo_count >= min_photos_threshold
                
                # 智能提示：给用户性能优化建议
                if not config_enabled and photo_count >= 50:
                    self.logger.info("💡 性能提示：检测到 %d 张待识别照片，建议开启并行识别以加速处理", photo_count)
                    self.logger.info("   方法1：在 config.json 中设置 parallel_recognition.enabled: true")
                    self.logger.info("   方法2：使用环境变量 SUNDAY_PHOTOS_PARALLEL=1")
                    estimated_time_serial = photo_count * 1.5  # 假设串行1.5秒/张
                    estimated_time_parallel = photo_count * 0.5  # 假设并行0.5秒/张
                    self.logger.info("   预计可节省: %.0f秒 → %.0f秒", estimated_time_serial, estimated_time_parallel)
                elif config_enabled and photo_count < min_photos_threshold:
                    self.logger.info("ℹ️  照片数量(%d张) < 并行阈值(%d张)，使用串行模式（小批量更稳定）", 
                                   photo_count, min_photos_threshold)

                if can_parallel:
                    try:
                        for photo_path, result in parallel_recognize(
                            to_recognize,
                            known_encodings=getattr(self.face_recognizer, 'known_encodings', []),
                            known_names=getattr(self.face_recognizer, 'known_student_names', []),
                            tolerance=tolerance,
                            min_face_size=min_face_size,
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
                        self.logger.debug("并行识别失败详情", exc_info=True)
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
            except Exception as e:
                # 缓存失败不影响主流程，但记录以便排查
                self.logger.debug(f"保存日期 {date} 的识别缓存失败: {e}")
                continue

        self.logger.info(f"✓ 人脸识别完成")
        self.logger.info(f"  - 识别到学生的照片: {self.stats['recognized_photos']} 张")
        self.logger.info(f"  - 无人脸照片: {no_face_count} 张")
        self.logger.info(f"  - unknown_photos: {self.stats['unknown_photos']} 张")
        self.logger.info(f"  - 处理出错照片: {error_count} 张")
        if self.stats['students_detected']:
            students_line = ', '.join(sorted(self.stats['students_detected']))
        else:
            students_line = '暂无'
        self.logger.info(f"  - 识别到的学生: {students_line}")

        all_unknown_photos = unknown_photos + no_face_photos + error_photos
        return recognition_results, all_unknown_photos, unknown_encodings_map

    def organize_output(self, recognition_results, unknown_photos, unknown_clusters=None):
        """组织输出目录"""
        self.logger.info(f"[步骤 4/4] 正在整理照片...")

        # 使用文件组织器整理照片
        stats = self.file_organizer.organize_photos(
            self.photos_dir,
            recognition_results,
            unknown_photos,
            unknown_clusters
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

                # 让最终统计能输出耗时
                self.stats['end_time'] = datetime.now()
                self.print_final_statistics()
                return True

            # 3. 处理照片，进行人脸识别并累积分类信息
            recognition_results, unknown_photos, unknown_encodings_map = self.process_photos(photo_files)

            # 3b. 对未知人脸进行聚类
            unknown_clusters = None
            if unknown_encodings_map:
                uc = self._get_config_loader().get_unknown_face_clustering()
                if uc.get('enabled'):
                    self.logger.info("正在对未知人脸进行聚类分析...")
                    clustering = UnknownClustering(
                        tolerance=float(uc.get('threshold', 0.45)),
                        min_cluster_size=int(uc.get('min_cluster_size', 2)),
                    )
                    for path, encodings in unknown_encodings_map.items():
                        # 仅对确实被归类为 unknown_photos 的照片进行聚类
                        # (虽然 unknown_encodings_map 可能包含部分识别成功但有多余人脸的照片，
                        # 但目前需求主要是整理 unknown_photos 目录)
                        if path in unknown_photos:
                            clustering.add_faces(path, encodings)

                    unknown_clusters = clustering.get_results()
                    if unknown_clusters:
                        self.logger.info(f"✓ 发现 {len(unknown_clusters)} 组相似的未知人脸")

            # 4. 整理输出目录（学生/日期分层；未知放 unknown_photos/日期）
            organize_stats = self.organize_output(recognition_results, unknown_photos, unknown_clusters)

            # 4b. 成功后写入增量快照
            if plan:
                save_snapshot(self.output_dir, plan.snapshot)

            # 5. 输出最终统计信息（先设置 end_time，确保耗时统计正确）
            self.stats['end_time'] = datetime.now()

            # 运行报告需要 end_time，这里用最终时间再生成一次（覆盖 organize_output 里的中间快照）
            self._build_run_report(organize_stats)
            self.print_final_statistics()

            return True

        except Exception as e:
            self.logger.exception(f"照片整理过程中发生错误")
            return False

        finally:
            # 兜底：如果上游分支未设置 end_time，这里补上
            if not self.stats.get('end_time'):
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
        self.logger.info(f"unknown_photos: {self.stats['unknown_photos']}")

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
        default_input_dir = DEFAULT_CONFIG['input_dir']
        default_output_dir = DEFAULT_CONFIG['output_dir']
        default_log_dir = DEFAULT_CONFIG['log_dir']
        default_tolerance = DEFAULT_CONFIG['tolerance']

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