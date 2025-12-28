from __future__ import annotations

from pathlib import Path

import pytest

from src.core.file_organizer import FileOrganizer
from src.core.scanner import Scanner


class _DummyReporter:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def log_info(self, level: str, message: str) -> None:
        self.messages.append((level, message))

    def log_rule(self) -> None:
        pass


def test_file_organizer_avoids_overwrite_by_suffix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """当两张不同来源、同名照片要复制到同一目录时，应自动加 _001 避免覆盖。"""

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    input_dir = tmp_path / "input"
    class_dir = input_dir / "class_photos"
    class_dir.mkdir(parents=True)

    src1 = class_dir / "a" / "group.jpg"
    src2 = class_dir / "b" / "group.jpg"
    src1.parent.mkdir(parents=True)
    src2.parent.mkdir(parents=True)

    src1.write_bytes(b"AAA")
    src2.write_bytes(b"BBB")

    monkeypatch.setattr("src.core.file_organizer.get_photo_date", lambda _p: "2025-12-27")

    organizer = FileOrganizer(output_dir=str(output_dir))
    stats = organizer.organize_photos(
        str(input_dir),
        recognition_results={str(src1): ["Alice"], str(src2): ["Alice"]},
        unknown_photos=[],
    )

    dest_dir = output_dir / "Alice" / "2025-12-27"
    assert dest_dir.exists()

    # 其中一个保留原名，另一个自动加后缀（顺序不保证）
    p0 = dest_dir / "group.jpg"
    p1 = dest_dir / "group_001.jpg"
    assert p0.exists()
    assert p1.exists()

    # 两个文件内容都应存在（不应互相覆盖）
    assert {p0.read_bytes(), p1.read_bytes()} == {b"AAA", b"BBB"}

    assert stats["copied"] == 2
    assert stats["students"]["Alice"] == 2


def test_scanner_root_photo_move_renames_on_conflict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """class_photos 根目录的照片归档到日期目录时，如目标已存在同名文件，应自动改名。"""

    class_photos = tmp_path / "input" / "class_photos"
    class_photos.mkdir(parents=True)

    date_dir = class_photos / "2025-12-27"
    date_dir.mkdir()

    # 目标日期目录里已有同名文件
    existing = date_dir / "photo.jpg"
    existing.write_bytes(b"OLD")

    # 根目录也有 photo.jpg（待归档）
    root_photo = class_photos / "photo.jpg"
    root_photo.write_bytes(b"NEW")

    # 固定日期，避免依赖 EXIF/mtime
    monkeypatch.setattr("src.core.scanner.get_photo_date", lambda _p: "2025-12-27")

    reporter = _DummyReporter()
    scanner = Scanner(photos_dir=class_photos, output_dir=tmp_path / "output", reporter=reporter)
    scanner.organize_input_by_date()

    assert not root_photo.exists()
    assert existing.read_bytes() == b"OLD"  # 不应被覆盖

    moved = date_dir / "photo_001.jpg"
    assert moved.exists()
    assert moved.read_bytes() == b"NEW"


def test_summary_report_contains_classification_breakdown(tmp_path: Path) -> None:
    """当 stats 提供 unknown/no-face/error 三类计数时，报告应包含分列统计段落。"""

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    organizer = FileOrganizer(output_dir=str(output_dir))

    report = organizer.create_summary_report(
        {
            "total": 3,
            "unique_photos": 3,
            "copied": 3,
            "failed": 0,
            "unknown_total": 1,
            "no_face_total": 1,
            "error_total": 1,
            "students": {"unknown_photos": 1, "no_face_photos": 1, "error_photos": 1},
        }
    )

    assert report is not None
    content = Path(report).read_text(encoding="utf-8")

    assert "分类统计（按原始照片张数）" in content
    assert "未识别（unknown_photos）" in content
    assert "无人脸（no_face_photos）" in content
    assert "出错（error_photos）" in content
