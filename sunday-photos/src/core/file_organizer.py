"""
文件组织和处理模块
负责照片的复制、目录创建和文件组织
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from .config import DEFAULT_OUTPUT_DIR, UNKNOWN_PHOTOS_DIR, REPORT_FILE, SMART_REPORT_FILE

from .utils import ensure_directory_exists, get_photo_date

logger = logging.getLogger(__name__)


class FileOrganizer:
    """文件组织器"""
    
    def __init__(self, output_dir=None):
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        self.output_dir = Path(output_dir)
        self.processed_files = 0
        self.copied_files = 0
        self.failed_files = 0
        
        # 确保输出目录存在
        ensure_directory_exists(self.output_dir)
    
    def organize_photos(self, input_dir, recognition_results, unknown_photos):
        """
        组织照片到相应的目录
        :param input_dir: 输入目录
        :param recognition_results: 识别结果字典 {photo_path: [student_names]}
        :param unknown_photos: 未知照片列表
        :return: 处理统计信息，包括总任务数、成功数、失败数、跳过数等
        """
        start_time = datetime.now()
        
        # 统计信息（按“复制任务”计数，避免多人合影时成功数 > 总数的统计偏差）
        total_copy_tasks = sum(len(names) for names in recognition_results.values()) + len(unknown_photos)
        stats = {
            'total': total_copy_tasks,
            'processed': 0,
            'copied': 0,
            'failed': 0,
            'students': {}
        }
        
        logger.info(f"开始整理照片，共 {stats['total']} 个复制任务")
        
        processed_photos = set()  # 用于检测重复照片

        # 使用进度条
        with tqdm(total=stats['total'], desc="整理照片", unit="张") as pbar:
            # 处理识别到的照片
            for photo_path, student_names in recognition_results.items():
                if photo_path in processed_photos:
                    stats['failed'] += 1  # 跳过重复照片
                    stats['skipped'] = stats.get('skipped', 0) + 1  # 记录跳过的照片数量
                    continue
                self._process_recognized_photo(photo_path, student_names, stats)
                processed_photos.add(photo_path)
                pbar.update(len(student_names))

            # 处理未知照片
            for photo_path in unknown_photos:
                if photo_path in processed_photos:
                    stats['failed'] += 1  # 跳过重复照片
                    stats['skipped'] = stats.get('skipped', 0) + 1  # 记录跳过的照片数量
                    continue
                self._process_unknown_photo(photo_path, stats)
                processed_photos.add(photo_path)
                pbar.update(1)
        
        # 计算耗时
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"照片整理完成，耗时: {elapsed:.2f}秒")
        logger.info(f"处理统计: 总计 {stats['total']} 个复制任务，成功 {stats['copied']}，失败 {stats['failed']}")
        
        # 输出每个学生的照片数量
        for student_name, count in stats['students'].items():
            logger.info(f"  {student_name}: {count} 张")
        
        return stats
    
    def _process_recognized_photo(self, photo_path, student_names, stats):
        """处理识别到的照片"""
        try:
            # 获取照片日期（输出目录按学生→日期分层）
            photo_date = get_photo_date(photo_path)
            
            # 为每个识别到的学生复制照片（学生/日期/文件）
            for student_name in student_names:
                student_dir = self.output_dir / student_name / photo_date
                ensure_directory_exists(student_dir)
                
                # 复制照片
                success = self._copy_photo(photo_path, student_dir)
                
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
            logger.error(f"处理照片 {photo_path} 失败: {str(e)}")
            stats['failed'] += len(student_names)
        
        # 按复制任务计数（多人合影按学生数累加）
        stats['processed'] += len(student_names)
    
    def _process_unknown_photo(self, photo_path, stats):
        """处理未知照片"""
        try:
            # 获取照片日期（输出目录按学生→日期分层；未知放独立日期目录）
            photo_date = get_photo_date(photo_path)
            unknown_dir = self.output_dir / UNKNOWN_PHOTOS_DIR / photo_date
            ensure_directory_exists(unknown_dir)
            
            # 复制照片
            success = self._copy_photo(photo_path, unknown_dir)
            
            if success:
                stats['copied'] += 1
                
                # 更新未知人脸统计
                if UNKNOWN_PHOTOS_DIR not in stats['students']:
                    stats['students'][UNKNOWN_PHOTOS_DIR] = 0
                stats['students'][UNKNOWN_PHOTOS_DIR] += 1
            else:
                stats['failed'] += 1
                logger.error(f"复制未知照片失败: {photo_path} -> {unknown_dir}")
        
        except Exception as e:
            logger.error(f"处理未知照片 {photo_path} 失败: {str(e)}")
            stats['failed'] += 1
        
        stats['processed'] += 1
    
    def _copy_photo(self, source_path, target_dir):
        """复制照片到目标目录"""
        try:
            # 生成目标文件名（避免重名）
            source_name = Path(source_path).stem
            source_ext = Path(source_path).suffix
            target_path = self._get_unique_filename(target_dir, source_name, source_ext)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            logger.debug(f"复制照片: {source_path} -> {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"复制照片失败: {str(e)}")
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
                f.write(f"  总照片数: {stats['total']}\n")
                f.write(f"  处理成功: {stats['copied']}\n")
                f.write(f"  处理失败: {stats['failed']}\n\n")
                
                f.write("各学生照片统计:\n")
                for student_name, count in stats['students'].items():
                    f.write(f"  {student_name}: {count} 张\n")
            
            logger.info(f"整理报告已保存: {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"创建整理报告失败: {str(e)}")
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
            logger.error(f"获取目录结构失败: {str(e)}")
        
        return structure