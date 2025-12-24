import pytest
from pathlib import Path

from src.core.student_manager import StudentManager, StudentPhotosLayoutError


def test_student_manager_selects_latest_five(offline_generated_dataset):
    # offline_generated_dataset 为 Alice 创建了 6 张参考照，mtime 递增。
    sm = StudentManager(input_dir=str(offline_generated_dataset.input_dir))

    alice = sm.students_data.get("Alice")
    assert alice is not None
    assert isinstance(alice, dict)
    assert len(alice["photo_paths"]) == 5

    # 期望最旧的一张 ref_01 被丢弃
    kept_names = {Path(p).name for p in alice["photo_paths"]}
    assert "ref_01.jpg" not in kept_names
    assert "ref_02.jpg" in kept_names
    assert "ref_06.jpg" in kept_names


def test_student_manager_raises_when_root_has_images(student_photos_root_image_input):
    with pytest.raises(StudentPhotosLayoutError):
        _ = StudentManager(input_dir=str(student_photos_root_image_input))
