#!/usr/bin/env python3
"""
扩展测试：验证学生管理和人脸识别在大规模数据下的稳定性。
生成30个学生数据并通过mock的人脸识别接口确保不会依赖真实图片。

合理性说明：
- 该测试的目标是验证：
    - StudentManager 能在较多学生数量下稳定扫描与构建索引
    - FaceRecognizer 能在 mock 的 face_recognition 接口下稳定完成匹配流程
- 由于底层识别函数被完整 mock，本测试不需要真实可解码的图片文件；
    只需要“文件存在且非空”以通过上层的输入校验。
"""
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

# 确保可以导入src模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

from student_manager import StudentManager
from face_recognizer import FaceRecognizer


def _create_dummy_photos(base_dir: Path, student_count: int = 30) -> None:
    student_photos = base_dir / "student_photos"
    student_photos.mkdir(parents=True, exist_ok=True)
    for i in range(1, student_count + 1):
        name = f"Student{i:02d}_1.jpg"
        (student_photos / name).write_bytes(b"fake-image-data")

    # 课堂照片目录仅用于传递路径给识别函数
    class_photos = base_dir / "class_photos"
    class_photos.mkdir(parents=True, exist_ok=True)
    (class_photos / "group.jpg").write_bytes(b"fake-class-photo")


class StudentManagerScalabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="scalability_input_"))
        _create_dummy_photos(self.temp_dir, student_count=30)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _mock_recognition_defaults(self, mock_load, mock_locs, mock_enc, mock_cmp, mock_dist):
        mock_load.return_value = np.zeros((128, 128, 3))
        mock_locs.return_value = [(0, 80, 120, 0)]  # 满足MIN_FACE_SIZE
        mock_enc.return_value = [np.zeros((128,))]

        def _fake_compare_faces(known_encodings, face_encoding, tolerance):
            # 标记第一位同学匹配，其他为False，确保匹配路径可控
            return [True] + [False] * (len(known_encodings) - 1)

        def _fake_face_distance(known_encodings, face_encoding):
            if not known_encodings:
                return np.array([])
            # 递增距离保证argmin为第一个同学
            return np.linspace(0.1, 1.0, num=len(known_encodings))

        mock_cmp.side_effect = _fake_compare_faces
        mock_dist.side_effect = _fake_face_distance

    @patch("face_recognizer.face_recognition.face_distance")
    @patch("face_recognizer.face_recognition.compare_faces")
    @patch("face_recognizer.face_recognition.face_encodings")
    @patch("face_recognizer.face_recognition.face_locations")
    @patch("face_recognizer.face_recognition.load_image_file")
    def test_student_manager_handles_30_students(self, mock_load, mock_locs, mock_enc, mock_cmp, mock_dist):
        self._mock_recognition_defaults(mock_load, mock_locs, mock_enc, mock_cmp, mock_dist)

        manager = StudentManager(input_dir=self.temp_dir)
        self.assertEqual(len(manager.get_student_names()), 30)
        self.assertTrue(all(name.startswith("Student") for name in manager.get_student_names()))

        recognizer = FaceRecognizer(manager)
        self.assertEqual(len(recognizer.known_student_names), 30)
        self.assertEqual(len(recognizer.known_encodings), 30)

        class_photo = self.temp_dir / "class_photos" / "group.jpg"
        result = recognizer.recognize_faces(str(class_photo), return_details=True)
        self.assertEqual(result.get("status"), "success")
        self.assertGreaterEqual(result.get("total_faces", 0), 1)
        self.assertIn("Student01", result.get("recognized_students", []))

    @patch("face_recognizer.face_recognition.face_distance")
    @patch("face_recognizer.face_recognition.compare_faces")
    @patch("face_recognizer.face_recognition.face_encodings")
    @patch("face_recognizer.face_recognition.face_locations")
    @patch("face_recognizer.face_recognition.load_image_file")
    def test_update_student_encoding_with_mock(self, mock_load, mock_locs, mock_enc, mock_cmp, mock_dist):
        self._mock_recognition_defaults(mock_load, mock_locs, mock_enc, mock_cmp, mock_dist)

        manager = StudentManager(input_dir=self.temp_dir)
        recognizer = FaceRecognizer(manager)

        new_photo = self.temp_dir / "class_photos" / "new_single.jpg"
        new_photo.write_bytes(b"fake-new-photo")

        updated = recognizer.update_student_encoding("Student15", str(new_photo))
        self.assertTrue(updated)
        self.assertIn("Student15", recognizer.known_student_names)


if __name__ == "__main__":
    unittest.main()
