import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.core.config import REPORT_FILE, UNKNOWN_PHOTOS_DIR
from src.core.file_organizer import FileOrganizer
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from tests.testdata_builder import build_dataset


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


def _stable_int(s: str) -> int:
    # Deterministic across processes/runs (avoid Python's hash randomization)
    return sum(s.encode("utf-8"))


class FakeFaceRecognizerRandomized:
    """离线随机化 e2e 测试用的识别替身（可预测、可复现）。

    规则（由 photo_path 决定，稳定且与 seed 解耦）：
    - 文件名以 "unknown_" 开头：unknown
    - 其余：
      - 若 stable_hash % 10 == 0 -> no_faces_detected
      - 否则 -> success，学生名按 stable_hash % len(students)
    """

    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "randomized-fp"
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        p = Path(photo_path)
        name = p.name

        if name.startswith("unknown_"):
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}

        h = _stable_int(p.as_posix())
        if h % 10 == 0:
            return {"status": "no_faces_detected", "recognized_students": [], "unknown_encodings": []}

        students = self.student_manager.get_student_names()
        chosen = students[h % len(students)] if students else "UNKNOWN"
        return {"status": "success", "recognized_students": [chosen], "unknown_encodings": []}


@dataclass
class SC:
    input_dir: Path
    output_dir: Path

    def __post_init__(self):
        self._student_manager = StudentManager(input_dir=str(self.input_dir))
        self._face_recognizer = FakeFaceRecognizerRandomized(self._student_manager)
        self._file_organizer = FileOrganizer(output_dir=str(self.output_dir))

    def get_student_manager(self):
        return self._student_manager

    def get_face_recognizer(self):
        return self._face_recognizer

    def get_file_organizer(self):
        return self._file_organizer


def _expected_destination(output_dir: Path, student_manager: StudentManager, photo_path: Path) -> Path:
    # photo_path is input/class_photos/<date>/<filename>
    date = photo_path.parent.name
    filename = photo_path.name

    if filename.startswith("unknown_"):
        return output_dir / UNKNOWN_PHOTOS_DIR / date / filename

    h = _stable_int(photo_path.as_posix())
    if h % 10 == 0:
        return output_dir / UNKNOWN_PHOTOS_DIR / date / filename

    students = student_manager.get_student_names()
    chosen = students[h % len(students)] if students else "UNKNOWN"
    return output_dir / chosen / date / filename


@pytest.mark.parametrize(
    "seed,student_count,date_count,photos_per_date,unknown_per_date",
    [
        (1, 5, 3, 3, 2),
        (7, 8, 4, 4, 1),
        (42, 10, 5, 3, 2),
        (99, 6, 6, 2, 2),
        (123, 12, 3, 5, 1),
    ],
)
def test_randomized_offline_pipeline_is_deterministic_and_complete(
    tmp_path: Path,
    seed: int,
    student_count: int,
    date_count: int,
    photos_per_date: int,
    unknown_per_date: int,
):
    """随机化回归测试：多组 seed 下自动构建数据、跑完整流水线、验证输出落盘。

    说明：这里的“随机”是指参数/数据由 seed 驱动生成，但对 CI/本地是可重复的，避免 flaky。
    """

    base = tmp_path / f"case_seed_{seed}"
    ds = build_dataset(
        base,
        seed=seed,
        student_count=student_count,
        date_count=date_count,
        photos_per_date=photos_per_date,
        unknown_per_date=unknown_per_date,
        empty_file_ratio=0.05,
    )

    config_path = ds.input_dir.parent / "config.json"
    _write_min_config(config_path)

    sc = SC(ds.input_dir, ds.output_dir)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=sc,
        config_file=str(config_path),
    )

    assert organizer.run() is True

    # 报告与增量快照应生成
    reports = list(ds.output_dir.glob(f"*_{REPORT_FILE}"))
    assert len(reports) == 1
    assert (ds.output_dir / ".state" / "class_photos_snapshot.json").exists()

    # 对每个非空课堂照片：应按识别结果落到目标路径（student 或 unknown）
    class_photos = sorted(ds.class_dir.rglob("*.jpg"))
    assert class_photos, "randomized dataset should contain class photos"

    for p in class_photos:
        if p.stat().st_size == 0:
            # 0 字节坏文件应被忽略，不强制要求输出
            continue

        expected = _expected_destination(ds.output_dir, sc.get_student_manager(), p)
        assert expected.exists(), f"expected output missing: {expected}"
