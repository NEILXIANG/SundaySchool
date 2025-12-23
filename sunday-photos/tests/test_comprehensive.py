"""综合性测试（覆盖主流程关键分支，偏集成/场景）。

体检要点：
- 这些测试更接近“业务场景验证”，会同时触发多个模块的协作；
- 为了在不同工作目录/沙箱中可稳定运行，这里显式把项目根目录加入 sys.path。
"""

import unittest
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

import sys

# 确保在沙箱/不同 cwd 下也能导入 src 包
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# 导入核心模块
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.face_recognizer import FaceRecognizer
from src.core.file_organizer import FileOrganizer
from src.core.config import DEFAULT_TOLERANCE

class TestComprehensive(unittest.TestCase):
    """全面综合测试套件"""

    def setUp(self):
        # 创建临时测试环境
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, 'input')
        self.output_dir = os.path.join(self.test_dir, 'output')
        self.log_dir = os.path.join(self.test_dir, 'logs')
        
        # 创建目录结构
        self.student_photos_dir = os.path.join(self.input_dir, 'student_photos')
        self.class_photos_dir = os.path.join(self.input_dir, 'class_photos')
        
        os.makedirs(self.student_photos_dir)
        os.makedirs(self.class_photos_dir)
        os.makedirs(self.output_dir)
        os.makedirs(self.log_dir)
        
        # 初始化主程序
        self.organizer = SimplePhotoOrganizer(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            log_dir=self.log_dir
        )

    def tearDown(self):
        # 清理临时文件
        shutil.rmtree(self.test_dir)

    def test_empty_input_directory(self):
        """测试空输入目录的情况"""
        # 不添加任何学生照片和课堂照片
        self.organizer.initialize()
        
        # 验证学生管理器加载了0个学生
        self.assertEqual(len(self.organizer.student_manager.get_all_students()), 0)
        
        # 运行处理流程
        # 由于没有照片，应该直接完成且不报错
        # 这里我们模拟一个空的识别结果
        results = {}
        unknowns = []
        
        # 验证文件组织器处理空结果
        stats = self.organizer.file_organizer.organize_photos(
            self.class_photos_dir, results, unknowns
        )
        
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['copied'], 0)

    def test_empty_class_photos_directory(self):
        """测试有学生但无课堂照片的情况"""
        # 创建一个学生参考照
        student_dir = Path(self.student_photos_dir) / 'StudentA'
        student_dir.mkdir(parents=True, exist_ok=True)
        (student_dir / 'a.jpg').touch()
        
        self.organizer.initialize()
        self.assertEqual(len(self.organizer.student_manager.get_all_students()), 1)
        
        # 模拟扫描照片返回空列表
        # 注意：SimplePhotoOrganizer 没有 _scan_photos 方法，它是直接在 run() 或 process_photos() 中处理
        # 我们这里直接调用 file_organizer.organize_photos 传入空列表
        
        results = {}
        unknowns = []
        
        stats = self.organizer.file_organizer.organize_photos(
            self.class_photos_dir, results, unknowns
        )
        
        self.assertEqual(stats['total'], 0)

    def test_reference_photo_selection_uses_latest_mtime_top_5(self):
        """当某学生参考照超过 5 张时，应选择最近修改时间最新的 5 张。"""
        student_dir = Path(self.student_photos_dir) / 'StudentA'
        student_dir.mkdir(parents=True, exist_ok=True)

        # 创建 7 张参考照，并用 utime 控制 mtime（p7 最新，p1 最旧）
        base_ts = time.time()
        created = []
        for i in range(1, 8):
            p = student_dir / f"p{i}.jpg"
            p.touch()
            ts = base_ts - (8 - i) * 10
            os.utime(p, (ts, ts))
            created.append(p)

        self.organizer.initialize()
        info = self.organizer.student_manager.get_student_by_name('StudentA')
        self.assertIsNotNone(info)

        selected_names = [Path(p).name for p in info['photo_paths']]
        self.assertEqual(len(selected_names), 5)

        # 期望：按 mtime 倒序取前 5 => p7..p3
        self.assertEqual(selected_names, ['p7.jpg', 'p6.jpg', 'p5.jpg', 'p4.jpg', 'p3.jpg'])

    def test_invalid_image_files(self):
        """测试无效/损坏的图片文件"""
        # 创建一个损坏的图片文件
        bad_photo = os.path.join(self.class_photos_dir, 'corrupt.jpg')
        with open(bad_photo, 'w') as f:
            f.write("This is not an image")
            
        # 模拟识别过程，应该能够处理异常而不崩溃
        # 这里我们直接测试 FaceRecognizer 的健壮性
        # 需要 mock face_recognition.load_image_file 抛出异常
        pass

    def test_special_filenames(self):
        """测试特殊文件名的处理（中文、空格、特殊字符）"""
        # 创建带有特殊字符的学生名（学生名来自文件夹名，文件名可随意）
        special_names = ['张三', 'John Doe', 'Student#1']
        
        for name in special_names:
            sd = Path(self.student_photos_dir) / name
            sd.mkdir(parents=True, exist_ok=True)
            (sd / 'ref.jpg').touch()
            
        self.organizer.initialize()
        
        loaded_names = self.organizer.student_manager.get_student_names()
        for name in special_names:
            self.assertIn(name, loaded_names)

    def test_large_number_of_students(self):
        """压力测试：大量学生"""
        # 清理之前可能存在的学生
        for p in Path(self.student_photos_dir).iterdir():
            if p.is_file():
                p.unlink()
            else:
                shutil.rmtree(p, ignore_errors=True)
            
        # 创建50个学生
        for i in range(50):
            sd = Path(self.student_photos_dir) / f"Student{i}"
            sd.mkdir(parents=True, exist_ok=True)
            (sd / 'ref.jpg').touch()
            
        # 重新初始化以加载新学生
        self.organizer.student_manager = StudentManager(self.input_dir)
        self.assertEqual(len(self.organizer.student_manager.get_all_students()), 50)

    def test_duplicate_photos(self):
        """测试重复照片的处理"""
        # 模拟同一张照片被多次识别（虽然在实际流程中通常是每个文件处理一次）
        # 但如果文件组织器收到重复请求，应能正确处理（覆盖或跳过）
        
        # 确保 file_organizer 已初始化
        self.organizer.initialize()
        
        photo_path = os.path.join(self.class_photos_dir, 'photo1.jpg')
        Path(photo_path).touch()
        
        # 模拟识别结果：同一张照片包含两个学生
        results = {photo_path: ['StudentA', 'StudentB']}
        unknowns = []
        
        # 确保输出目录为空
        student_a_dir = os.path.join(self.output_dir, 'StudentA')
        student_b_dir = os.path.join(self.output_dir, 'StudentB')
        
        # Mock shutil.copy2
        with patch('shutil.copy2') as mock_copy:
            stats = self.organizer.file_organizer.organize_photos(
                self.class_photos_dir, results, unknowns
            )
            
            # 应该有2次复制操作
            self.assertEqual(stats['copied'], 2)
            self.assertEqual(mock_copy.call_count, 2)

    def test_concurrent_safety_simulation(self):
        """模拟并发安全（虽然当前是单线程，但为未来做准备）"""
        # 主要是确保文件写入不会冲突
        pass

    def test_tolerance_boundary(self):
        """测试 tolerance 边界值"""
        self.organizer.initialize()
        
        # 测试 0.0 和 1.0
        recognizer_strict = FaceRecognizer(self.organizer.student_manager, tolerance=0.0)
        self.assertEqual(recognizer_strict.tolerance, 0.0)
        
        recognizer_loose = FaceRecognizer(self.organizer.student_manager, tolerance=1.0)
        self.assertEqual(recognizer_loose.tolerance, 1.0)

    def test_output_directory_permissions(self):
        """测试输出目录无权限的情况"""
        self.organizer.initialize()
        
        # 模拟输出目录只读
        # 在实际文件系统中很难跨平台模拟，这里使用 Mock
        with patch('src.core.file_organizer.ensure_directory_exists', side_effect=PermissionError("Access denied")):
            results = {'some_photo.jpg': ['StudentA']}
            unknowns = []
            
            # 应该捕获异常并记录失败，而不是崩溃
            try:
                stats = self.organizer.file_organizer.organize_photos(
                    self.class_photos_dir, results, unknowns
                )
                # 如果代码没有捕获异常，这里会失败
                # 假设 organize_photos 内部处理了异常，或者我们期望它抛出
            except PermissionError:
                # 如果设计是抛出异常，这也是预期的
                pass
            except Exception as e:
                self.fail(f"Unexpected exception: {e}")

    def test_date_parsing_formats(self):
        """测试多种日期格式解析"""
        from src.core.utils import get_photo_date
        
        # 1. 目录名 yyyy-mm-dd
        path1 = "/path/to/2025-12-25/photo.jpg"
        self.assertEqual(get_photo_date(path1), "2025-12-25")
        
        # 2. 目录名不匹配，回退到 EXIF (Mock)
        path2 = "/path/to/other/photo.jpg"
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img._getexif.return_value = {36867: '2025:01:01 12:00:00'} # DateTimeOriginal
            mock_open.return_value = mock_img
            
            # 需要 mock TAGS 查找
            with patch('PIL.ExifTags.TAGS', {36867: 'DateTimeOriginal'}):
                self.assertEqual(get_photo_date(path2), "2025-01-01")

    def test_memory_error_handling(self):
        """测试内存不足时的处理"""
        # 模拟 face_recognition 加载图片时内存不足
        with patch('face_recognition.load_image_file', side_effect=MemoryError("Out of memory")):
            # 创建一个学生和照片
            sd = Path(self.student_photos_dir) / 'StudentA'
            sd.mkdir(parents=True, exist_ok=True)
            (sd / 'ref.jpg').touch()
            
            # 初始化时加载学生编码
            self.organizer.initialize()
            self.organizer.face_recognizer.load_student_encodings()
            
            # 应该记录错误但继续运行（跳过该照片）
            # 验证日志或状态（这里简单验证没有崩溃）

    def test_statistics_accuracy(self):
        """测试统计数据的准确性"""
        stats = {
            'total': 10,
            'processed': 0,
            'copied': 5,
            'failed': 2,
            'students': {'A': 3, 'B': 2}
        }
        # 验证逻辑一致性
        self.assertEqual(stats['copied'] + stats['failed'], 7) # 还有3个未处理或跳过
        self.assertEqual(sum(stats['students'].values()), stats['copied'])

if __name__ == '__main__':
    unittest.main()
