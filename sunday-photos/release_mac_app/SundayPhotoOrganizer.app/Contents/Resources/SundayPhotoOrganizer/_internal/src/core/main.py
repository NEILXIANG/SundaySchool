"""
主程序入口
主日学课堂照片自动整理工具

管线概览（四步）：
1) 初始化组件（学生管理、人脸识别、文件组织）；
2) 扫描输入目录并按日期归档课堂照片；
3) 执行人脸识别，区分成功/未匹配/无人脸/错误；
4) 将照片按“学生/日期”写入输出目录并生成报告。
"""

import sys
import os
import logging
import argparse
import warnings
from pathlib import Path
from datetime import datetime

# 忽略 pkg_resources 弃用警告（不影响运行）
warnings.filterwarnings("ignore", message=r"pkg_resources is deprecated as an API\.")

from .utils.logger import setup_logger
from .utils.fs import ensure_directory_exists
from .config import DEFAULT_CONFIG
from .config_loader import ConfigLoader
from .container import ServiceContainer
from .pipeline import Pipeline
from .parallel_recognizer import parallel_recognize # Re-export for backward compat if needed
from .clustering import UnknownClustering # Re-export for backward compat
from .recognition_cache import invalidate_date_cache
from .incremental_state import save_snapshot

# Re-export ServiceContainer for backward compatibility
__all__ = ["SimplePhotoOrganizer", "ServiceContainer", "ConfigLoader", "parallel_recognize", "UnknownClustering"]

class SimplePhotoOrganizer:
    """
    照片整理器主类（支持依赖注入容器）
    Facade for the new Pipeline architecture.
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
        
        ensure_directory_exists(self.input_dir)
        ensure_directory_exists(self.input_dir / DEFAULT_CONFIG['class_photos_dir'])
        ensure_directory_exists(self.input_dir / DEFAULT_CONFIG['student_photos_dir'])
        ensure_directory_exists(self.output_dir)
        ensure_directory_exists(self.log_dir)
        
        self.logger = setup_logger(self.log_dir, enable_color_console=True)
        self.service_container = service_container
        self._config_file = config_file
        self._config_loader = None
        
        self.initialized = False
        self._pipeline = None
        self._internal_incremental_plan = None
        
        # Backward compatibility attributes
        self.student_manager = None
        self.face_recognizer = None
        self.file_organizer = None
        self.stats = {}
        self.last_run_report = None

    @property
    def _incremental_plan(self):
        if self._pipeline and self._pipeline.scanner:
            return self._pipeline.scanner.incremental_plan
        return self._internal_incremental_plan

    @_incremental_plan.setter
    def _incremental_plan(self, value):
        self._internal_incremental_plan = value
        if self._pipeline and self._pipeline.scanner:
            self._pipeline.scanner.incremental_plan = value

    def _get_config_loader(self) -> ConfigLoader:
        if self._config_loader is None:
            if self._config_file:
                cfg_path = Path(self._config_file)
                self._config_loader = ConfigLoader(str(cfg_path), base_dir=cfg_path.parent)
            else:
                self._config_loader = ConfigLoader()
        return self._config_loader

    def initialize(self, force=False):
        """初始化各个组件"""
        # Check if critical components are missing even if initialized=True
        if self.initialized and not force:
            if self.service_container and self._pipeline:
                self.logger.debug("系统组件已初始化，跳过重复初始化")
                return True
            # If missing components, proceed with initialization
            self.logger.debug("系统标记为已初始化但组件缺失，重新初始化")

        try:
            # 1. Setup ServiceContainer if not provided
            if not self.service_container:
                # Inject config into container
                cfg = self._get_config_loader()
                
                # Propagate backend choice to env
                try:
                    engine = str(getattr(cfg, 'get_face_backend_engine')()).strip().lower()
                except Exception:
                    engine = "insightface"
                if not os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND"):
                    os.environ["SUNDAY_PHOTOS_FACE_BACKEND"] = engine

                container_config = {
                    'input_dir': self.input_dir,
                    'output_dir': self.output_dir,
                    'log_dir': self.log_dir,
                    'tolerance': float(getattr(cfg, 'get_tolerance')()),
                    'min_face_size': int(getattr(cfg, 'get_min_face_size')()),
                }
                self.service_container = ServiceContainer(container_config)
                self.logger.debug(f"Created ServiceContainer: {self.service_container}")

            # 2. Initialize services (trigger lazy loading)
            # If attributes were set manually (e.g. mocks in tests), inject them into container
            if self.student_manager:
                self.service_container._services['student_manager'] = self.student_manager
            else:
                self.student_manager = self.service_container.get_student_manager()

            if self.face_recognizer:
                self.service_container._services['face_recognizer'] = self.face_recognizer
            else:
                self.face_recognizer = self.service_container.get_face_recognizer()

            if self.file_organizer:
                self.service_container._services['file_organizer'] = self.file_organizer
            else:
                self.file_organizer = self.service_container.get_file_organizer()

            # 3. Check student photos
            missing_photos = self.student_manager.check_student_photos()
            if missing_photos:
                self.logger.warning(f"警告: 有 {len(missing_photos)} 名学生缺少参考照片")

            # 4. Initialize Pipeline for backward compatibility methods
            if not self._pipeline:
                self.logger.debug(f"Creating Pipeline with container: {self.service_container}")
                self._pipeline = Pipeline(
                    self.service_container,
                    self.input_dir,
                    self.output_dir,
                    self.log_dir,
                    self._get_config_loader(),
                    parallel_recognize_fn=(lambda *args, **kwargs: parallel_recognize(*args, **kwargs)),
                )
                # Inject incremental plan if set before pipeline creation
                if self._internal_incremental_plan:
                    self._pipeline.scanner.incremental_plan = self._internal_incremental_plan

            self.initialized = True
            return True

        except Exception as e:
            self.logger.exception(f"系统初始化失败: {str(e)}")
            self.initialized = False
            return False

    def scan_input_directory(self):
        """[Deprecated] Delegate to Pipeline.scanner.scan()"""
        if not self._pipeline:
            self.initialize()
        return self._pipeline.scanner.scan()

    def process_photos(self, photo_files):
        """[Deprecated] Delegate to Pipeline.process_photos()"""
        if not self._pipeline:
            self.initialize()
        res = self._pipeline.process_photos(photo_files)
        self.stats = self._pipeline.stats # Sync stats
        return res

    def organize_output(self, recognition_results, unknown_photos, no_face_photos=None, error_photos=None, unknown_clusters=None):
        """[Deprecated] Delegate to Pipeline.organize_output()"""
        if not self._pipeline:
            self.initialize()
        return self._pipeline.organize_output(recognition_results, unknown_photos, no_face_photos, error_photos, unknown_clusters)

    def _cleanup_output_for_dates(self, dates):
        """[Deprecated] Delegate to Pipeline._cleanup_output_for_dates()"""
        if not self._pipeline:
            self.initialize()
        return self._pipeline._cleanup_output_for_dates(dates)

    def run(self):
        """运行照片整理流程"""
        if not self.initialized:
            if not self.initialize():
                return False

        # Ensure pipeline exists for the default delegate methods; allow tests to
        # monkeypatch instance methods (scan/process/organize/cleanup) without requiring container.
        if not self._pipeline and self.service_container:
            self._pipeline = Pipeline(
                self.service_container,
                self.input_dir,
                self.output_dir,
                self.log_dir,
                self._get_config_loader(),
                parallel_recognize_fn=(lambda *args, **kwargs: parallel_recognize(*args, **kwargs)),
            )
            if self._internal_incremental_plan:
                self._pipeline.scanner.incremental_plan = self._internal_incremental_plan

        try:
            # 2) Scan (instance method is patchable in tests)
            photo_files = self.scan_input_directory()

            # Keep pipeline stats consistent with Pipeline.run()
            if self._pipeline:
                self._pipeline.stats['total_photos'] = len(photo_files)

            # Prefer explicitly injected incremental plan (tests), else use pipeline scanner plan.
            plan = self._incremental_plan
            if plan is None and self._pipeline and getattr(self._pipeline, 'scanner', None):
                plan = self._pipeline.scanner.incremental_plan

            changed_dates = getattr(plan, 'changed_dates', set()) if plan else set()
            deleted_dates = getattr(plan, 'deleted_dates', set()) if plan else set()

            # 2b) Cleanup for changed/deleted dates (may require pipeline)
            if self._pipeline:
                self._cleanup_output_for_dates(sorted(changed_dates | deleted_dates))
            for date in sorted(deleted_dates):
                invalidate_date_cache(self.output_dir, date)

            if not photo_files:
                if deleted_dates and plan is not None and getattr(plan, 'snapshot', None) is not None:
                    save_snapshot(self.output_dir, plan.snapshot)
                if self._pipeline:
                    self._pipeline.stats['end_time'] = datetime.now()
                    self._pipeline.reporter.print_final_statistics(self._pipeline.stats, self.output_dir)
                    self.stats = self._pipeline.stats
                    self.last_run_report = self._pipeline.last_run_report
                return True

            # 3) Process (instance method patchable; default delegates to Pipeline)
            processed = self.process_photos(photo_files)
            # Backward compatibility: tests/legacy code may monkeypatch process_photos to return
            # (recognition_results, unknown_photos, unknown_encodings_map)
            if isinstance(processed, tuple) and len(processed) == 3:
                recognition_results, unknown_photos, unknown_encodings_map = processed
                no_face_photos = []
                error_photos = []
            else:
                recognition_results, unknown_photos, no_face_photos, error_photos, unknown_encodings_map = processed

            # 3b) Unknown clustering (use main.UnknownClustering so tests patching organizer_module work)
            unknown_clusters = None
            if unknown_encodings_map:
                try:
                    uc = self._get_config_loader().get_unknown_face_clustering()
                except Exception:
                    uc = {}
                if uc.get('enabled'):
                    clustering = UnknownClustering(
                        tolerance=float(uc.get('threshold', 0.45)),
                        min_cluster_size=int(uc.get('min_cluster_size', 2)),
                    )
                    for path, encodings in unknown_encodings_map.items():
                        if path in unknown_photos:
                            clustering.add_faces(path, encodings)
                    unknown_clusters = clustering.get_results()

            # 4) Organize output (instance method patchable; default delegates to Pipeline)
            organize_stats = None
            try:
                organize_stats = self.organize_output(recognition_results, unknown_photos, no_face_photos, error_photos, unknown_clusters)
            except TypeError:
                # Backward compatibility: older override signature organize_output(recognition_results, unknown_photos, unknown_clusters)
                combined_unknown = list(unknown_photos or []) + list(no_face_photos or []) + list(error_photos or [])
                organize_stats = self.organize_output(recognition_results, combined_unknown, unknown_clusters)

            if organize_stats is None:
                organize_stats = {}

            if plan is not None and getattr(plan, 'snapshot', None) is not None:
                save_snapshot(self.output_dir, plan.snapshot)

            # Sync stats/report if pipeline is present
            if self._pipeline:
                self._pipeline.stats['end_time'] = datetime.now()
                self._pipeline.last_run_report = self._pipeline.reporter.build_run_report(self._pipeline.stats, organize_stats)
                self._pipeline.reporter.print_final_statistics(self._pipeline.stats, self.output_dir)
                self.stats = self._pipeline.stats
                self.last_run_report = self._pipeline.last_run_report

            return True
        except Exception:
            self.logger.exception("照片整理过程中发生错误")
            return False


def parse_arguments(config_loader=None):
    """解析命令行参数"""
    if config_loader:
        default_input_dir = config_loader.get_input_dir()
        default_output_dir = config_loader.get_output_dir()
        default_log_dir = config_loader.get_log_dir()
        default_tolerance = config_loader.get_tolerance()
    else:
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
    config_loader = ConfigLoader()
    args = parse_arguments(config_loader)

    organizer = SimplePhotoOrganizer(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir
    )
    
    if not organizer.initialize():
        sys.exit(1)
    
    if hasattr(organizer, 'face_recognizer'):
        organizer.face_recognizer.tolerance = args.tolerance

    success = organizer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
