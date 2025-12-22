#!/usr/bin/env python3
"""
业务逻辑场景测试
测试复杂的人脸识别和文件归档场景

说明：
- 本文件主要验证“识别器/组织器”的业务逻辑分支是否正确，而非验证真实模型精度。
- 对 face_recognition 的耗时/不稳定部分全部用 mock 替代，确保测试稳定可复现。
"""

import os
import sys
import unittest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

# 添加 src 目录到路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.face_recognizer import FaceRecognizer
from core.file_organizer import FileOrganizer
from core.student_manager import StudentManager
from core.config import UNKNOWN_PHOTOS_DIR

class TestLogicScenarios(unittest.TestCase):
    def setUp(self):
        # 创建临时目录结构
        self.test_dir = Path(tempfile.mkdtemp())
        self.input_dir = self.test_dir / "input"
        self.output_dir = self.test_dir / "output"
        self.student_photos_dir = self.input_dir / "student_photos"
        self.class_photos_dir = self.input_dir / "class_photos"
        
        # 创建目录
        self.input_dir.mkdir()
        self.output_dir.mkdir()
        self.student_photos_dir.mkdir()
        self.class_photos_dir.mkdir()
        
        # 模拟学生管理器：默认返回空学生列表，避免 FaceRecognizer.__init__ 触发不必要的文件读取
        self.student_manager = MagicMock(spec=StudentManager)
        self.student_manager.get_all_students.return_value = []
        
        # 模拟人脸编码 (128维向量)
        # 注意：这里使用固定种子，确保测试完全可复现（避免偶发失败）。
        rng = np.random.default_rng(20251222)
        self.encoding_zhang = rng.random(128)
        self.encoding_li = rng.random(128)
        self.encoding_wang = rng.random(128)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('face_recognition.load_image_file')
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    def test_multiple_reference_photos(self, mock_encodings, mock_locations, mock_load_image):
        """测试场景1: 学生有多张参考照片"""
        print("\n🧪 测试场景1: 多张参考照片逻辑")
        
        # 准备数据：ZhangSan 有两张照片
        self.student_manager.get_all_students.return_value = [
            {
                'name': 'ZhangSan', 
                'photo_paths': [
                    str(self.student_photos_dir / 'ZhangSan_1.jpg'),
                    str(self.student_photos_dir / 'ZhangSan_2.jpg')
                ]
            }
        ]
        
        # 创建虚拟文件
        (self.student_photos_dir / 'ZhangSan_1.jpg').touch()
        (self.student_photos_dir / 'ZhangSan_2.jpg').touch()
        
        # 模拟 face_recognition 行为：
        # - 第一张照片检测不到人脸 => 跳过
        # - 第二张照片检测到人脸且尺寸足够大 => 生成编码并写入 students_encodings
        mock_locations.side_effect = [[], [(10, 100, 100, 10)]]
        mock_encodings.side_effect = [[self.encoding_zhang]] # 只有第二次调用会用到这个
        
        # 初始化识别器
        recognizer = FaceRecognizer(self.student_manager)
        
        # 验证
        # 应该尝试加载了两张照片
        self.assertEqual(mock_load_image.call_count, 2)
        # 最终应该成功加载了 ZhangSan
        self.assertIn('ZhangSan', recognizer.students_encodings)
        # 编码应该是第二张照片的
        np.testing.assert_array_equal(recognizer.students_encodings['ZhangSan']['encoding'], self.encoding_zhang)
        print("✅ 成功处理多张参考照片，自动跳过无效照片")

    @patch('face_recognition.load_image_file')
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    @patch('face_recognition.face_distance')
    @patch('face_recognition.compare_faces')
    def test_group_photo_recognition(self, mock_compare, mock_distance, mock_encodings, mock_locations, mock_load_image):
        """测试场景2: 多人合照识别"""
        print("\n🧪 测试场景2: 多人合照识别")
        
        # 准备已加载的学生编码
        # 初始化识别器（会加载空学生列表），随后手动注入 known faces
        recognizer = FaceRecognizer(self.student_manager)
        recognizer.students_encodings = {
            'ZhangSan': {'name': 'ZhangSan', 'encoding': self.encoding_zhang},
            'LiSi': {'name': 'LiSi', 'encoding': self.encoding_li}
        }
        recognizer._refresh_known_faces()
        print(f"DEBUG: known_names={recognizer.known_student_names}")
        print(f"DEBUG: known_encodings len={len(recognizer.known_encodings)}")
        
        # 模拟一张合照，包含 ZhangSan 和 LiSi
        photo_path = str(self.class_photos_dir / "group.jpg")
        Path(photo_path).touch()
        
        # 模拟检测到两个人脸 (注意尺寸要大于 MIN_FACE_SIZE=50)
        # (top, right, bottom, left)
        # Face 1: 100-10=90 > 50
        # Face 2: 200-110=90 > 50
        mock_locations.return_value = [(10, 100, 100, 10), (110, 200, 200, 110)]
        # 模拟这两个人脸的编码
        face1 = self.encoding_zhang
        face2 = self.encoding_li
        mock_encodings.return_value = [face1, face2]
        
        # 模拟比较结果
        # 第一次循环：face1 (ZhangSan)
        # compare_faces([Zhang, Li], face1) -> [True, False]
        # face_distance([Zhang, Li], face1) -> [0.01, 0.8]
        
        # 第二次循环：face2 (LiSi)
        # compare_faces([Zhang, Li], face2) -> [False, True]
        # face_distance([Zhang, Li], face2) -> [0.8, 0.01]
        
        mock_compare.side_effect = [
            [True, False],
            [False, True]
        ]
        
        mock_distance.side_effect = [
            np.array([0.01, 0.8]), 
            np.array([0.8, 0.01])
        ]
        
        # 执行识别
        results = recognizer.recognize_faces(photo_path)
        
        # 验证结果
        self.assertIn('ZhangSan', results)
        self.assertIn('LiSi', results)
        self.assertEqual(len(results), 2)
        print("✅ 成功识别合照中的多个人物")

    @patch('core.file_organizer.get_photo_date')
    def test_file_organization_logic(self, mock_get_date):
        """测试场景3: 文件归档逻辑 (多人 + 日期)"""
        print("\n🧪 测试场景3: 文件归档逻辑")
        
        organizer = FileOrganizer(output_dir=self.output_dir)
        
        # 模拟数据
        photo_path = str(self.class_photos_dir / "group.jpg")
        Path(photo_path).touch()
        
        recognition_results = {
            photo_path: ['ZhangSan', 'LiSi']
        }
        unknown_photos = []
        
        # 模拟照片日期
        mock_get_date.return_value = "2023-10-01"
        
        # 执行整理
        stats = organizer.organize_photos(self.input_dir, recognition_results, unknown_photos)
        
        # 验证
        # 1. 检查统计数据
        self.assertEqual(stats['copied'], 2)
        self.assertEqual(stats['students']['ZhangSan'], 1)
        self.assertEqual(stats['students']['LiSi'], 1)
        
        # 2. 检查文件系统
        zhang_file = self.output_dir / "ZhangSan" / "2023-10-01" / "group.jpg"
        lisi_file = self.output_dir / "LiSi" / "2023-10-01" / "group.jpg"
        
        self.assertTrue(zhang_file.exists(), "ZhangSan 的照片未创建")
        self.assertTrue(lisi_file.exists(), "LiSi 的照片未创建")
        print("✅ 文件正确归档到对应的学生和日期目录")

    @patch('face_recognition.load_image_file')
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    @patch('face_recognition.face_distance')
    @patch('face_recognition.compare_faces')
    def test_tolerance_boundary(self, mock_compare, mock_distance, mock_encodings, mock_locations, mock_load_image):
        """测试场景4: 阈值边界测试"""
        print("\n🧪 测试场景4: 阈值边界测试")
        
        recognizer = FaceRecognizer(self.student_manager, tolerance=0.6)
        recognizer.students_encodings = {
            'ZhangSan': {'name': 'ZhangSan', 'encoding': self.encoding_zhang}
        }
        recognizer._refresh_known_faces()
        
        photo_path = str(self.class_photos_dir / "test.jpg")
        Path(photo_path).touch()
        
        # 模拟检测到一个人脸 (尺寸 > 50)
        mock_locations.return_value = [(10, 100, 100, 10)]
        mock_encodings.return_value = [self.encoding_zhang] # 编码本身不重要，结果由 mock 决定
        
        # Case 1: 距离 0.59 (应该匹配)
        mock_distance.return_value = np.array([0.59])
        mock_compare.return_value = [True]
        
        results1 = recognizer.recognize_faces(photo_path)
        self.assertIn('ZhangSan', results1, "0.59 应该小于 0.6 从而匹配")
        
        # Case 2: 距离 0.61 (应该不匹配)
        mock_distance.return_value = np.array([0.61])
        mock_compare.return_value = [False]
        
        results2 = recognizer.recognize_faces(photo_path)
        self.assertEqual(results2, [], "0.61 应该大于 0.6 从而不匹配")
        
        print("✅ 阈值边界判断正确")

    @patch('core.file_organizer.get_photo_date')
    def test_unknown_photo_handling(self, mock_get_date):
        """测试场景5: 未知照片处理"""
        print("\n🧪 测试场景5: 未知照片处理")
        
        organizer = FileOrganizer(output_dir=self.output_dir)
        mock_get_date.return_value = "2023-12-25"
        
        photo_path = str(self.class_photos_dir / "stranger.jpg")
        Path(photo_path).touch()
        
        # 模拟没有识别出任何人
        recognition_results = {}
        unknown_photos = [photo_path]
        
        organizer.organize_photos(self.input_dir, recognition_results, unknown_photos)
        
        # 验证是否进入 unknown_photos 目录
        # 使用常量，避免目录名未来变更导致测试失效
        unknown_file = self.output_dir / UNKNOWN_PHOTOS_DIR / "2023-12-25" / "stranger.jpg"
        self.assertTrue(unknown_file.exists(), "未知照片应该被归档到 unknown_photos")
        print("✅ 未知照片正确归档")

if __name__ == '__main__':
    unittest.main()
