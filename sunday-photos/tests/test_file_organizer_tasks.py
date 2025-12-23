#!/usr/bin/env python3
"""FileOrganizer 扩展测试：统计与输出结构校验。

合理性说明：
- 这里关注的是“文件复制/输出结构/统计计数”的正确性，而不是图片解码。
- 因此输入文件内容使用简单字节即可（非真实 JPEG/PNG 也可），
    避免引入 PIL/face_recognition 等外部依赖与不稳定因素。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)

from core.file_organizer import FileOrganizer  # noqa: E402
from core.config import UNKNOWN_PHOTOS_DIR  # noqa: E402


def _touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake")


class FileOrganizerTaskTests(unittest.TestCase):
    """验证多学生、多任务的复制统计与输出结构。

    覆盖点：
    - 同一张照片复制到多名学生目录
    - 单名学生复制多张照片
    - 未识别照片进入 UNKNOWN 目录
    - 统计字段 total/copied/failed/processed/students 的一致性
    """

    def test_multi_student_counts_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_root = base / "input"
            output_root = base / "output"
            class_dir = input_root / "class_photos"

            date1 = class_dir / "2025-12-21"
            date2 = class_dir / "2025-12-28"

            photo1 = date1 / "p1.jpg"  # 将被复制给两名学生
            photo2 = date1 / "p2.png"  # 将被复制给一名学生
            photo3 = date2 / "p3.jpg"  # 未匹配人脸

            for p in (photo1, photo2, photo3):
                _touch(p)

            recognition_results = {
                str(photo1): ["张三", "李四"],
                str(photo2): ["张三"],
            }
            unknown_photos = [str(photo3)]

            organizer = FileOrganizer(output_dir=output_root)
            stats = organizer.organize_photos(class_dir, recognition_results, unknown_photos)

            # 复制任务总数 = 2(张三+李四) + 1(张三) + 1(未知) = 4
            self.assertEqual(stats["total"], 4)
            self.assertEqual(stats["copied"], 4)
            self.assertEqual(stats["failed"], 0)
            self.assertEqual(stats["processed"], 4)

            self.assertEqual(stats["students"].get("张三"), 2)
            self.assertEqual(stats["students"].get("李四"), 1)
            self.assertEqual(stats["students"].get(UNKNOWN_PHOTOS_DIR), 1)

            # 输出结构存在
            self.assertTrue((output_root / "张三" / "2025-12-21" / "p1.jpg").exists())
            self.assertTrue((output_root / "张三" / "2025-12-21" / "p2.png").exists())
            self.assertTrue((output_root / "李四" / "2025-12-21" / "p1.jpg").exists())
            self.assertTrue((output_root / UNKNOWN_PHOTOS_DIR / "2025-12-28" / "p3.jpg").exists())


if __name__ == "__main__":
    unittest.main()
