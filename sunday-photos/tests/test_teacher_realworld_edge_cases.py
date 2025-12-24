import json
import re
from pathlib import Path

import pytest

from src.core.config import UNKNOWN_PHOTOS_DIR
from src.core.file_organizer import FileOrganizer
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentPhotosLayoutError
from src.core.student_manager import StudentManager
from tests.testdata_builder import write_empty_file, write_jpeg


DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class FakeFaceRecognizerAlwaysAlice:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, _photo_path: str, return_details: bool = True):
        return {"status": "success", "recognized_students": ["Alice"], "unknown_encodings": []}


class FakeFaceRecognizerAllUnknown:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, _photo_path: str, return_details: bool = True):
        return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}


class FakeServiceContainer:
    def __init__(self, input_dir: Path, output_dir: Path, recognizer_mode: str):
        self._student_manager = StudentManager(input_dir=str(input_dir))
        if recognizer_mode == "alice":
            self._face_recognizer = FakeFaceRecognizerAlwaysAlice(self._student_manager)
        elif recognizer_mode == "unknown":
            self._face_recognizer = FakeFaceRecognizerAllUnknown(self._student_manager)
        else:
            raise ValueError(f"Unknown recognizer_mode: {recognizer_mode}")
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


def _count_jpgs(dir_path: Path) -> int:
    if not dir_path.exists():
        return 0
    return len(list(dir_path.rglob("*.jpg")))


def test_teacher_puts_reference_photos_in_student_photos_root_still_runs(tmp_path: Path):
    """老师把参考照直接丢到 student_photos/ 根目录：
    - 这是常见误操作：系统应给出清晰的错误提示（而不是静默错误或产生混乱输出）
    """
    base = tmp_path
    input_dir = base / "input"
    student_root = input_dir / "student_photos"
    class_dir = input_dir / "class_photos"
    output_dir = base / "output"
    log_dir = base / "logs"

    # 错误用法：student_photos 根目录放图片
    write_jpeg(student_root / "Alice_ref_should_be_in_folder.jpg", text="ref", seed=1)

    # 课堂照（正常放法）
    write_jpeg(class_dir / "2025-12-27" / "group.jpg", text="class", seed=2)

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_path = base / "config.json"
    _write_min_config(config_path)

    with pytest.raises(StudentPhotosLayoutError) as exc:
        organizer = SimplePhotoOrganizer(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            log_dir=str(log_dir),
            service_container=FakeServiceContainer(input_dir, output_dir, recognizer_mode="unknown"),
            config_file=str(config_path),
        )
        organizer.run()
    msg = str(exc.value)
    assert "student_photos 根目录" in msg
    assert "唯一正确方式" in msg
    assert "Alice_ref_should_be_in_folder.jpg" in msg


def test_teacher_puts_class_photos_in_root_are_auto_moved_and_processed(tmp_path: Path):
    """老师直接把课堂照丢到 class_photos/ 根目录：
    - 程序会按日期移动到 YYYY-MM-DD/ 子目录（日期来自 mtime）
    - 不要求老师提前建日期文件夹
    """
    base = tmp_path
    input_dir = base / "input"
    student_dir = input_dir / "student_photos" / "Alice"
    class_dir = input_dir / "class_photos"
    output_dir = base / "output"
    log_dir = base / "logs"

    # 学生参考照（正常）
    write_jpeg(student_dir / "ref.jpg", text="Alice", seed=10)

    # 课堂照直接放根目录
    write_jpeg(class_dir / "root_photo.jpg", text="root", seed=11)

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_path = base / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=FakeServiceContainer(input_dir, output_dir, recognizer_mode="alice"),
        config_file=str(config_path),
    )

    assert organizer.run() is True

    # 根目录应不再直接包含该图片
    assert not (class_dir / "root_photo.jpg").exists()

    moved = list(class_dir.rglob("root_photo.jpg"))
    assert len(moved) == 1
    date_dir = moved[0].parent
    assert DATE_DIR_RE.match(date_dir.name)

    # 输出应按学生/日期生成
    alice_out = output_dir / "Alice" / date_dir.name
    assert alice_out.exists()
    assert _count_jpgs(alice_out) >= 1


def test_mixed_physical_date_dirs_same_day_are_merged_into_one_output_date(tmp_path: Path):
    """同一天存在多种物理目录写法（英文月份名/带备注等），输出应归一到同一个 YYYY-MM-DD。"""
    base = tmp_path
    input_dir = base / "input"
    student_dir = input_dir / "student_photos" / "Alice"
    class_dir = input_dir / "class_photos"
    output_dir = base / "output"
    log_dir = base / "logs"

    write_jpeg(student_dir / "ref.jpg", text="Alice", seed=20)

    write_jpeg(class_dir / "Dec 26 2025" / "a.jpg", text="a", seed=21)
    write_jpeg(class_dir / "2025-12-26 活动" / "b.jpg", text="b", seed=22)

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_path = base / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=FakeServiceContainer(input_dir, output_dir, recognizer_mode="alice"),
        config_file=str(config_path),
    )

    assert organizer.run() is True

    merged_out = output_dir / "Alice" / "2025-12-26"
    assert merged_out.exists()
    assert _count_jpgs(merged_out) >= 2


def test_metadata_and_zero_byte_files_in_class_photos_are_ignored(tmp_path: Path):
    """老师常见的系统文件/坏文件：.DS_Store、._ 前缀、0字节图片。
    程序应忽略它们，不应导致崩溃或产生无意义输出。
    """
    base = tmp_path
    input_dir = base / "input"
    student_dir = input_dir / "student_photos" / "Alice"
    date_dir = input_dir / "class_photos" / "2025-12-27"
    output_dir = base / "output"
    log_dir = base / "logs"

    write_jpeg(student_dir / "ref.jpg", text="Alice", seed=30)

    # 1 张有效照片
    write_jpeg(date_dir / "ok.jpg", text="ok", seed=31)

    # 平台垃圾/隐藏/坏文件
    (date_dir / ".DS_Store").write_text("x", encoding="utf-8")
    (date_dir / "._ok.jpg").write_text("x", encoding="utf-8")
    write_empty_file(date_dir / "empty.jpg")

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    config_path = base / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        service_container=FakeServiceContainer(input_dir, output_dir, recognizer_mode="alice"),
        config_file=str(config_path),
    )

    assert organizer.run() is True

    out_dir = output_dir / "Alice" / "2025-12-27"
    assert out_dir.exists()
    assert _count_jpgs(out_dir) == 1
