import json
from pathlib import Path

from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from src.core.file_organizer import FileOrganizer
from tests.testdata_builder import write_jpeg


class FakeFaceRecognizerAlwaysAlice:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, _photo_path: str, return_details: bool = True):
        return {"status": "success", "recognized_students": ["Alice"], "unknown_encodings": []}


class FakeServiceContainer:
    def __init__(self, input_dir: Path, output_dir: Path):
        self._student_manager = StudentManager(input_dir=str(input_dir))
        self._face_recognizer = FakeFaceRecognizerAlwaysAlice(self._student_manager)
        self._file_organizer = FileOrganizer(output_dir=str(output_dir))

    def get_student_manager(self):
        return self._student_manager

    def get_face_recognizer(self):
        return self._face_recognizer

    def get_file_organizer(self):
        return self._file_organizer


def _write_min_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "parallel_recognition": {"enabled": False, "workers": 1, "chunk_size": 1, "min_photos": 9999},
                "unknown_face_clustering": {"enabled": False},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_input_date_dir_formats_are_accepted_and_output_is_normalized(tmp_path: Path):
    input_dir = tmp_path / "input"
    student_dir = input_dir / "student_photos" / "Alice"
    class_dir = input_dir / "class_photos"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    # 学生参考照
    write_jpeg(student_dir / "ref.jpg", text="Alice", seed=1)

    # 课堂照：使用多种日期目录格式
    write_jpeg(class_dir / "2025.12.21" / "img_01.jpg", text="d1", seed=2)
    write_jpeg(class_dir / "2025年12月22日" / "img_01.jpg", text="d2", seed=3)
    write_jpeg(class_dir / "2025/12/23" / "img_01.jpg", text="d3", seed=4)
    write_jpeg(class_dir / "2025-12-24 周日" / "img_01.jpg", text="d4", seed=5)
    write_jpeg(class_dir / "2025年12月25日_圣诞活动" / "img_01.jpg", text="d5", seed=6)
    write_jpeg(class_dir / "Dec 26 2025" / "img_01.jpg", text="d6", seed=7)
    write_jpeg(class_dir / "27 Dec 2025" / "img_01.jpg", text="d7", seed=8)
    write_jpeg(class_dir / "December 28, 2025" / "img_01.jpg", text="d8", seed=9)

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    config_path = tmp_path / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=FakeServiceContainer(input_dir, output_dir),
        config_file=str(config_path),
    )

    assert organizer.run() is True

    # 输出日期应统一为 YYYY-MM-DD
    assert (output_dir / "Alice" / "2025-12-21").exists()
    assert (output_dir / "Alice" / "2025-12-22").exists()
    assert (output_dir / "Alice" / "2025-12-23").exists()
    assert (output_dir / "Alice" / "2025-12-24").exists()
    assert (output_dir / "Alice" / "2025-12-25").exists()
    assert (output_dir / "Alice" / "2025-12-26").exists()
    assert (output_dir / "Alice" / "2025-12-27").exists()
    assert (output_dir / "Alice" / "2025-12-28").exists()
