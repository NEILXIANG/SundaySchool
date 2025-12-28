"""
Processing Pipeline.
"""
import os
import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from typing import Dict, List

from .utils.logger import COLORS
from .utils.fs import ensure_resolved_under, UnsafePathError
from .utils.date_parser import get_photo_date, parse_date_from_text
from .config import DEFAULT_CONFIG, UNKNOWN_PHOTOS_DIR, NO_FACE_PHOTOS_DIR, ERROR_PHOTOS_DIR
from .incremental_state import save_snapshot
from .recognition_cache import (
    CacheKey,
    compute_params_fingerprint,
    invalidate_date_cache,
    load_date_cache,
    normalize_cache_for_fingerprint,
    lookup_result,
    store_result,
    prune_entries,
    save_date_cache_atomic,
)
from .parallel_recognizer import parallel_recognize
from .clustering import UnknownClustering
from .reporter import Reporter
from .scanner import Scanner

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, container, input_dir, output_dir, log_dir, config_loader, parallel_recognize_fn=None):
        self.container = container
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.config_loader = config_loader
        self._parallel_recognize = parallel_recognize_fn or parallel_recognize
        self.photos_dir = self.input_dir / DEFAULT_CONFIG['class_photos_dir']
        
        self.reporter = Reporter(logger)
        self.scanner = Scanner(self.photos_dir, self.output_dir, self.reporter)
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_photos': 0,
            'processed_photos': 0,
            'recognized_photos': 0,
            'unknown_photos': 0,
            'no_face_photos': 0,
            'error_photos': 0,
            'students_detected': set()
        }
        self.last_run_report = None

    def _reset_stats(self):
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_photos': 0,
            'processed_photos': 0,
            'recognized_photos': 0,
            'unknown_photos': 0,
            'no_face_photos': 0,
            'error_photos': 0,
            'students_detected': set()
        }

    def _cleanup_output_for_dates(self, dates):
        if not dates:
            return

        def _safe_delete_dir(path: Path) -> None:
            try:
                ensure_resolved_under(self.output_dir, path)
            except UnsafePathError as e:
                logger.warning(f"跳过不安全清理路径: {path} ({e})")
                return

            try:
                if path.is_symlink():
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        return
                    except Exception:
                        return

                if path.exists() and path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                return

        for top in self.output_dir.iterdir():
            if top.name.startswith('.'): # is_ignored_fs_entry simplified
                continue
            if not top.is_dir():
                continue

            for date in dates:
                date_dir = top / date
                if date_dir.exists() and date_dir.is_dir():
                    _safe_delete_dir(date_dir)

            if top.name == UNKNOWN_PHOTOS_DIR:
                for date in dates:
                    date_dir = top / date
                    if date_dir.exists() and date_dir.is_dir():
                        _safe_delete_dir(date_dir)

                for cluster_dir in top.iterdir():
                    if cluster_dir.name.startswith('.'):
                        continue
                    if not cluster_dir.is_dir():
                        continue
                    if not cluster_dir.name.startswith("Unknown_Person_"):
                        continue
                    for date in dates:
                        date_dir = cluster_dir / date
                        if date_dir.exists() and date_dir.is_dir():
                            _safe_delete_dir(date_dir)

            if top.name in (NO_FACE_PHOTOS_DIR, ERROR_PHOTOS_DIR):
                for date in dates:
                    date_dir = top / date
                    if date_dir.exists() and date_dir.is_dir():
                        _safe_delete_dir(date_dir)

    def _extract_date_and_rel(self, photo_path: str) -> tuple[str, str]:
        p = Path(photo_path)
        try:
            rel = p.relative_to(self.photos_dir).as_posix()
        except (ValueError, OSError) as e:
            logger.debug(f"照片 {photo_path} 路径解析异常，使用文件名: {e}")
            rel = p.name
        parts = rel.split('/')
        if parts:
            normalized = parse_date_from_text(parts[0] or "")
            if normalized:
                return normalized, rel
        return get_photo_date(photo_path), rel

    def process_photos(self, photo_files):
        self.reporter.log_rule()
        self.reporter.log_info("STEP", "3/4 人脸识别（检测 → 匹配 → 分类）")

        recognition_results = {}
        unknown_photos = []
        no_face_photos = []
        error_photos = []
        unknown_encodings_map = {}

        def _apply_result(photo_path: str, result: dict) -> None:
            recognized_students = result.get('recognized_students') or []
            status = result.get('status')
            
            if 'unknown_encodings' in result and result['unknown_encodings']:
                unknown_encodings_map[photo_path] = result['unknown_encodings']

            if status == 'success':
                recognition_results[photo_path] = recognized_students
                self.stats['recognized_photos'] += 1
                self.stats['students_detected'].update(recognized_students)
                logger.debug(f"识别到: {os.path.basename(photo_path)} -> {', '.join(recognized_students)}")
            elif status == 'no_faces_detected':
                no_face_photos.append(photo_path)
                self.stats['no_face_photos'] += 1
                logger.debug(f"无人脸: {os.path.basename(photo_path)}")
            elif status == 'no_matches_found':
                unknown_photos.append(photo_path)
                self.stats['unknown_photos'] += 1
                logger.debug(f"未识别到已知学生: {os.path.basename(photo_path)}")
            else:
                error_photos.append(photo_path)
                self.stats['error_photos'] += 1
                msg = result.get('message', '')
                logger.error(f"识别出错: {os.path.basename(photo_path)} - {msg}")

            self.stats['processed_photos'] += 1

        face_recognizer = self.container.get_face_recognizer()
        tolerance = float(getattr(face_recognizer, 'tolerance', DEFAULT_CONFIG['tolerance']))
        min_face_size = int(getattr(face_recognizer, 'min_face_size', DEFAULT_CONFIG['min_face_size']))
        params_fingerprint = compute_params_fingerprint(
            {
                'tolerance': tolerance,
                'min_face_size': min_face_size,
                'reference_fingerprint': str(getattr(face_recognizer, 'reference_fingerprint', '')),
            }
        )
        date_to_cache = {}
        keep_rel_paths_by_date = {}
        photo_to_key = {}
        to_recognize = []
        cache_hit_count = 0

        # Progress bar setup (simplified for brevity, keeping core logic)
        bar_format_warm = "{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}] {postfix}"
        bar_format_full = "{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}"
        
        with tqdm(
            total=len(photo_files),
            desc="[AI] 人脸识别",
            unit="张",
            dynamic_ncols=True,
            mininterval=0.2,
            smoothing=0.05,
            bar_format=bar_format_warm,
        ) as pbar:
            import time
            
            # ... (Progress bar helpers omitted for brevity, can be copied if needed or simplified) ...
            # For now, using simple updates.
            
            # 1) Cache lookup
            for photo_path in photo_files:
                try:
                    date, rel_path = self._extract_date_and_rel(photo_path)
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
                        if pbar.n > 0: pbar.bar_format = bar_format_full
                    else:
                        to_recognize.append(photo_path)
                        photo_to_key[photo_path] = key
                except Exception as e:
                    logger.exception(f"处理照片 {photo_path} 时发生异常")
                    error_photos.append(photo_path)
                    error_count += 1
                    self.stats['processed_photos'] += 1
                    pbar.update(1)

            # 2) Recognition
            if to_recognize:
                logger.info(f"✓ 识别缓存命中: {cache_hit_count} 张；待识别: {len(to_recognize)} 张")
                
                parallel_cfg = self.config_loader.get_parallel_recognition()
                config_enabled = bool(parallel_cfg.get('enabled'))
                min_photos_threshold = int(parallel_cfg.get('min_photos', 30))
                photo_count = len(to_recognize)
                workers = int(parallel_cfg.get('workers', 1))
                chunk_size = int(parallel_cfg.get('chunk_size', 1))
                
                can_parallel = config_enabled and photo_count >= min_photos_threshold and workers > 1
                
                if can_parallel:
                    logger.info("🚀 启用并行识别")
                    try:
                        for photo_path, result in self._parallel_recognize(
                            to_recognize,
                            known_encodings=getattr(face_recognizer, 'known_encodings', []),
                            known_names=getattr(face_recognizer, 'known_student_names', []),
                            tolerance=tolerance,
                            min_face_size=min_face_size,
                            workers=workers,
                            chunk_size=chunk_size,
                        ):
                            _apply_result(photo_path, result)
                            key = photo_to_key.get(photo_path)
                            if key is not None:
                                store_result(date_to_cache[key.date], key, result)
                            pbar.update(1)
                            if pbar.n > 0: pbar.bar_format = bar_format_full
                    except Exception as e:
                        logger.warning(f"并行识别失败，回退串行: {e}")
                        for photo_path in to_recognize:
                            result = face_recognizer.recognize_faces(photo_path, return_details=True)
                            _apply_result(photo_path, result)
                            key = photo_to_key.get(photo_path)
                            if key is not None:
                                store_result(date_to_cache[key.date], key, result)
                            pbar.update(1)
                else:
                    for photo_path in to_recognize:
                        result = face_recognizer.recognize_faces(photo_path, return_details=True)
                        _apply_result(photo_path, result)
                        key = photo_to_key.get(photo_path)
                        if key is not None:
                            store_result(date_to_cache[key.date], key, result)
                        pbar.update(1)
            else:
                logger.info(f"✓ 识别缓存命中: {cache_hit_count} 张；待识别: 0 张")

        # 3) Save cache
        for date, cache in date_to_cache.items():
            try:
                prune_entries(cache, keep_rel_paths_by_date.get(date, set()))
                save_date_cache_atomic(self.output_dir, date, cache)
            except Exception as e:
                logger.debug(f"保存日期 {date} 的识别缓存失败: {e}")
                continue

        self.reporter.log_info("STAT", f"识别到学生的照片: {self.stats['recognized_photos']} 张")
        self.reporter.log_info("STAT", f"无人脸照片: {self.stats['no_face_photos']} 张")
        self.reporter.log_info("STAT", f"unknown_photos: {self.stats['unknown_photos']} 张")
        self.reporter.log_info("STAT", f"处理出错照片: {self.stats['error_photos']} 张")
        self.reporter.log_rule()

        return recognition_results, unknown_photos, no_face_photos, error_photos, unknown_encodings_map

    def organize_output(self, recognition_results, unknown_photos, no_face_photos=None, error_photos=None, unknown_clusters=None):
        self.reporter.log_rule()
        self.reporter.log_info("STEP", "4/4 输出整理（复制到 output/ + 生成报告）")

        file_organizer = self.container.get_file_organizer()
        stats = file_organizer.organize_photos(
            self.photos_dir,
            recognition_results,
            unknown_photos,
            unknown_clusters,
            no_face_photos=no_face_photos,
            error_photos=error_photos,
        )

        report_file = file_organizer.create_summary_report(stats)
        self.reporter.log_info("OK", "照片整理完成")
        if report_file:
            self.reporter.log_info("OK", f"整理报告已生成: {report_file}")

        self.last_run_report = self.reporter.build_run_report(self.stats, stats)
        return stats

    def run(self, photo_files=None):
        self._reset_stats()
        self.last_run_report = None
        self.stats['start_time'] = datetime.now()

        try:
            # 1. Initialize (assumed done by caller or container)
            
            # 2. Scan
            if photo_files is None:
                photo_files = self.scanner.scan()
            
            self.stats['total_photos'] = len(photo_files)
            
            plan = self.scanner.incremental_plan
            changed_dates = getattr(plan, 'changed_dates', set()) if plan else set()
            deleted_dates = getattr(plan, 'deleted_dates', set()) if plan else set()

            self._cleanup_output_for_dates(sorted(changed_dates | deleted_dates))

            for date in sorted(deleted_dates):
                invalidate_date_cache(self.output_dir, date)

            if not photo_files:
                if deleted_dates:
                    logger.info("✓ 本次无新增/变更照片，仅执行了删除同步")
                    if plan:
                        save_snapshot(self.output_dir, plan.snapshot)
                else:
                    logger.info("✓ 本次无需处理：没有新增/变更/删除的日期文件夹")

                self.stats['end_time'] = datetime.now()
                self.reporter.print_final_statistics(self.stats, self.output_dir)
                return True

            # 3. Process
            recognition_results, unknown_photos, no_face_photos, error_photos, unknown_encodings_map = self.process_photos(photo_files)

            # 3b. Clustering
            unknown_clusters = None
            if unknown_encodings_map:
                uc = self.config_loader.get_unknown_face_clustering()
                if uc.get('enabled'):
                    logger.info("正在对未知人脸进行聚类分析...")
                    clustering = UnknownClustering(
                        tolerance=float(uc.get('threshold', 0.45)),
                        min_cluster_size=int(uc.get('min_cluster_size', 2)),
                    )
                    for path, encodings in unknown_encodings_map.items():
                        if path in unknown_photos:
                            clustering.add_faces(path, encodings)

                    unknown_clusters = clustering.get_results()
                    if unknown_clusters:
                        logger.info(f"✓ 发现 {len(unknown_clusters)} 组相似的未知人脸")

            # 4. Organize
            organize_stats = self.organize_output(recognition_results, unknown_photos, no_face_photos, error_photos, unknown_clusters)

            if plan:
                save_snapshot(self.output_dir, plan.snapshot)

            self.stats['end_time'] = datetime.now()
            self.last_run_report = self.reporter.build_run_report(self.stats, organize_stats)
            self.reporter.print_final_statistics(self.stats, self.output_dir)

            return True

        except Exception as e:
            logger.exception(f"照片整理过程中发生错误")
            return False
        finally:
            if not self.stats.get('end_time'):
                self.stats['end_time'] = datetime.now()
