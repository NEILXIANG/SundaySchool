"""文件组织与落盘模块。

职责：
- 根据识别结果把照片复制到输出目录（学生/日期/照片文件）；
- 将未匹配到学生的照片放入 UNKNOWN 目录（按日期分层）；
- 生成整理报告（便于教师核对本次整理结果）。

统计口径：
- 以“复制任务”为单位计数：一张多人合影若识别到 N 名学生，会产生 N 次复制任务。
    这样能避免“成功数 > 总数”的统计歧义。
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from .config import DEFAULT_OUTPUT_DIR, UNKNOWN_PHOTOS_DIR, REPORT_FILE, SMART_REPORT_FILE

from .utils import ensure_directory_exists, ensure_resolved_under, get_photo_date, safe_join_under, UnsafePathError

logger = logging.getLogger(__name__)


class FileOrganizer:
    """文件组织器（只负责复制与目录结构，不做识别）。"""
    
    def __init__(self, output_dir=None):
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        self.output_dir = Path(output_dir)
        self.processed_files = 0
        self.copied_files = 0
        self.failed_files = 0
        
        # 确保输出目录存在
        ensure_directory_exists(self.output_dir)
    
    def organize_photos(self, input_dir, recognition_results, unknown_photos, unknown_clusters=None):
        """把识别结果落盘到输出目录，并返回统计信息。

        参数：
        - input_dir：输入目录（当前实现中主要用于日志语义，逻辑上不依赖）
        - recognition_results：{photo_path: [student_names]}，同一照片可能对应多个学生
        - unknown_photos：未识别到任何已知学生的照片路径列表
        - unknown_clusters：{cluster_name: [photo_paths]} 未知人脸聚类结果

        返回：
        - stats：按“复制任务”统计的字典（total/copied/failed/processed 等）

        备注：
        - 为避免同一照片被重复处理，内部会用 processed_photos 集合去重。
        """
        start_time = datetime.now()
        
        # 预处理聚类映射：photo_path -> cluster_name
        photo_to_cluster = {}
        if unknown_clusters:
            for cluster_name, paths in unknown_clusters.items():
                for path in paths:
                    photo_to_cluster[path] = cluster_name

        # 统计信息（按“复制任务”计数，避免多人合影时成功数 > 总数的统计偏差）
        total_copy_tasks = sum(len(names) for names in recognition_results.values()) + len(unknown_photos)
        unique_photos = len(set(recognition_results.keys()) | set(unknown_photos))
        stats = {
            'total': total_copy_tasks,
            'unique_photos': unique_photos,
            'processed': 0,
            'copied': 0,
            'failed': 0,
            'students': {}
        }
        
        logger.info(f"开始整理照片，共 {stats['total']} 个复制任务")
        
        processed_photos = set()  # 用于检测重复照片
        copied_files = []  # 跟踪已复制的文件，用于错误恢复

        # 使用进度条
        with tqdm(total=stats['total'], desc="整理照片", unit="张") as pbar:
            try:
                # 处理识别到的照片
                for photo_path, student_names in recognition_results.items():
                    if photo_path in processed_photos:
                        stats['failed'] += 1  # 跳过重复照片
                        stats['skipped'] = stats.get('skipped', 0) + 1  # 记录跳过的照片数量
                        continue
                    self._process_recognized_photo(photo_path, student_names, stats, copied_files)
                    processed_photos.add(photo_path)
                    pbar.update(len(student_names))

                # 处理未知照片
                for photo_path in unknown_photos:
                    if photo_path in processed_photos:
                        stats['failed'] += 1  # 跳过重复照片
                        stats['skipped'] = stats.get('skipped', 0) + 1  # 记录跳过的照片数量
                        continue
                    
                    cluster_name = photo_to_cluster.get(photo_path)
                    self._process_unknown_photo(photo_path, stats, copied_files, cluster_name)
                    processed_photos.add(photo_path)
                    pbar.update(1)
            except Exception as e:
                logger.exception("整理过程中发生异常，开始回滚")
                self._rollback_copied_files(copied_files)
                raise
        
        # 计算耗时
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"照片整理完成，耗时: {elapsed:.2f}秒")
        logger.info(f"处理统计: 总计 {stats['total']} 个复制任务，成功 {stats['copied']}，失败 {stats['failed']}")
        
        # 输出每个学生的照片数量
        for student_name, count in stats['students'].items():
            logger.info(f"  {student_name}: {count} 张")
        
        return stats
    
    def _process_recognized_photo(self, photo_path, student_names, stats, copied_files=None):
        """处理识别到的照片"""
        try:
            # 获取照片日期（输出目录按学生→日期分层）
            photo_date = get_photo_date(photo_path)
            
            # 为每个识别到的学生复制照片（学生/日期/文件）
            for student_name in student_names:
                # 使用 safe_join_under 防止路径遍历攻击
                student_dir = safe_join_under(self.output_dir, student_name, photo_date)
                ensure_directory_exists(student_dir)
                
                # 复制照片
                success = self._copy_photo(photo_path, student_dir, copied_files)
                
                if success:
                    stats['copied'] += 1
                    
                    # 更新学生统计
                    if student_name not in stats['students']:
                        stats['students'][student_name] = 0
                    stats['students'][student_name] += 1
                else:
                    stats['failed'] += 1
                    
                    logger.error(f"复制照片失败: {photo_path} -> {student_dir}")
        
        except Exception as e:
            logger.exception(f"处理照片 {photo_path} 时发生异常")
            stats['failed'] += len(student_names)
        
        # 按复制任务计数（多人合影按学生数累加）
        stats['processed'] += len(student_names)
    
    def _process_unknown_photo(self, photo_path, stats, copied_files=None, cluster_name=None):
        """处理未知照片"""
        try:
            # 获取照片日期（输出目录按学生→日期分层；未知放独立日期目录）
            photo_date = get_photo_date(photo_path)
            
            # 确定目标目录
            if cluster_name:
                # 如果属于某个聚类，放入 output/unknown_photos/Unknown_Person_X/2024-01-01
                unknown_dir = safe_join_under(self.output_dir, UNKNOWN_PHOTOS_DIR, cluster_name, photo_date)
            else:
                # 否则放入 output/unknown_photos/2024-01-01
                unknown_dir = safe_join_under(self.output_dir, UNKNOWN_PHOTOS_DIR, photo_date)
                
            ensure_directory_exists(unknown_dir)
            
            # 复制照片
            success = self._copy_photo(photo_path, unknown_dir, copied_files)
            
            if success:
                stats['copied'] += 1
                
                # 更新未知人脸统计
                key = cluster_name if cluster_name else UNKNOWN_PHOTOS_DIR
                if key not in stats['students']:
                    stats['students'][key] = 0
                stats['students'][key] += 1
            else:
                stats['failed'] += 1
                logger.error(f"复制未知照片失败: {photo_path} -> {unknown_dir}")
        
        except Exception as e:
            logger.exception(f"处理未知照片 {photo_path} 时发生异常")
            stats['failed'] += 1
        
        stats['processed'] += 1
    
    def _copy_photo(self, source_path, target_dir, copied_files=None):
        """复制照片到目标目录"""
        try:
            # 生成目标文件名（避免重名）
            source_name = Path(source_path).stem
            source_ext = Path(source_path).suffix
            target_path = self._get_unique_filename(target_dir, source_name, source_ext)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            if copied_files is not None:
                copied_files.append(target_path)
            
            logger.debug(f"复制照片: {source_path} -> {target_path}")
            return True
            
        except Exception as e:
            logger.exception(f"复制照片失败: {source_path}")
            return False
    
    def _get_unique_filename(self, directory, base_name, extension):
        """生成唯一的文件名，避免重名"""
        counter = 1
        filename = f"{base_name}{extension}"
        target_path = directory / filename
        
        # 如果文件不存在，直接返回
        if not target_path.exists():
            return target_path
        
        # 添加序号直到找到不存在的文件名
        while target_path.exists():
            filename = f"{base_name}_{counter:03d}{extension}"
            target_path = directory / filename
            counter += 1
        
        return target_path
    
    def create_summary_report(self, stats):
        """创建整理总结报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.output_dir / f"{timestamp}_{REPORT_FILE}"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("主日学课堂照片整理报告\n")
                f.write("=" * 30 + "\n")
                f.write(f"整理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("处理统计:\n")
                # 注意：total/copy/copy_failed 以“复制任务”为单位（多人合影会复制到多个学生目录）
                if 'unique_photos' in stats:
                    f.write(f"  本次涉及原始照片: {stats['unique_photos']} 张\n")
                f.write(f"  总复制任务数: {stats['total']}\n")
                f.write(f"  成功复制任务: {stats['copied']}\n")
                f.write(f"  失败复制任务: {stats['failed']}\n\n")
                
                f.write("各学生照片统计:\n")
                for student_name, count in stats['students'].items():
                    f.write(f"  {student_name}: {count} 张\n")
            
            logger.info(f"整理报告已保存: {report_file}")
            return report_file
            
        except Exception as e:
            logger.exception("创建整理报告失败")
            return None
    
    def get_directory_structure(self):
        """获取输出目录结构"""
        structure = {}
        
        try:
            for root, dirs, files in os.walk(self.output_dir):
                # 计算相对路径
                rel_path = os.path.relpath(root, self.output_dir)
                if rel_path == '.':
                    rel_path = 'output'
                
                # 统计文件数量
                structure[rel_path] = {
                    'dirs': dirs,
                    'files': len(files)
                }
        except Exception as e:
            logger.exception("获取目录结构失败")
        
        return structure
    
    def _rollback_copied_files(self, copied_files):
        """回滚已复制的文件，在异常时清理"""
        if not copied_files:
            return
        
        logger.warning(f"开始回滚 {len(copied_files)} 个已复制文件")
        rolled_back = 0
        
        for dest_path in copied_files:
            try:
                try:
                    ensure_resolved_under(self.output_dir, dest_path)
                except UnsafePathError as e:
                    logger.warning(f"跳过不安全回滚路径: {dest_path} ({e})")
                    continue

                if dest_path.exists():
                    dest_path.unlink()  # 删除文件
                    rolled_back += 1
                    logger.debug(f"已回滚文件: {dest_path}")
                else:
                    logger.debug(f"文件不存在，跳过回滚: {dest_path}")
            except Exception as e:
                logger.error(f"回滚文件失败 {dest_path}: {e}")
        
        logger.info(f"回滚完成，已删除 {rolled_back}/{len(copied_files)} 个文件")