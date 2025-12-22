import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil

from src.core.file_organizer import FileOrganizer
from src.core.face_recognizer import FaceRecognizer
from src.core.student_manager import StudentManager

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_input_dir = Path("test_input")
        self.test_output_dir = Path("test_output")
        self.student_manager = StudentManager()  # 初始化 StudentManager
        self.test_input_dir.mkdir(exist_ok=True)
        self.test_output_dir.mkdir(exist_ok=True)

    def tearDown(self):
        for path in [self.test_input_dir, self.test_output_dir]:
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

    def test_empty_input_directory(self):
        """测试空输入目录的处理"""
        face_recognizer = FaceRecognizer(student_manager=self.student_manager)
        result = face_recognizer.load_reference_photos(self.test_input_dir)
        self.assertEqual(result, {}, "空输入目录应返回空字典")

    def test_no_reference_photos(self):
        """测试无参考照片的处理"""
        (self.test_input_dir / "random_file.txt").write_text("Not a photo")
        face_recognizer = FaceRecognizer(student_manager=self.student_manager)
        result = face_recognizer.load_reference_photos(self.test_input_dir)
        self.assertEqual(result, {}, "无参考照片时应返回空字典")

    def test_duplicate_photos(self):
        """测试重复照片的统计逻辑"""
        photo1 = self.test_input_dir / "photo1.jpg"
        photo2 = self.test_input_dir / "photo2.jpg"
        photo1.write_text("dummy content")
        photo2.write_text("dummy content")

        recognition_results = {
            photo1: ["Student1"],
            photo2: ["Student2"]
        }
        unknown_photos = [photo1]

        file_organizer = FileOrganizer(output_dir=self.test_output_dir)
        stats = file_organizer.organize_photos(self.test_input_dir, recognition_results, unknown_photos)

        self.assertEqual(stats["total"], 3, "总计应为3")
        self.assertEqual(stats["copied"], 2, "应复制2张唯一照片")
        self.assertEqual(stats["skipped"], 1, "应跳过1张重复照片")

if __name__ == "__main__":
    unittest.main()