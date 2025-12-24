import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.core.file_organizer import FileOrganizer
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager
from tests.testdata_builder import write_empty_file, write_jpeg


RUN_RANDOM = os.environ.get("SUNDAY_PHOTOS_RUN_RANDOM_TESTS", "").strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class RandomDataset:
    input_dir: Path
    class_dir: Path
    output_dir: Path
    log_dir: Path
    config_path: Path
    expected_nonempty_images: int


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
    def __init__(self, input_dir: Path, output_dir: Path):
        self._student_manager = StudentManager(input_dir=str(input_dir))
        self._face_recognizer = FakeFaceRecognizerAllUnknown(self._student_manager)
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


def _build_random_dataset(tmp_path: Path, seed: int) -> RandomDataset:
    rnd = random.Random(seed)

    base = tmp_path / f"seed_{seed}"
    input_dir = base / "input"
    class_dir = input_dir / "class_photos"
    output_dir = base / "output"
    log_dir = base / "logs"

    class_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日期目录：覆盖老师常见的多种写法（最终都会归一到 YYYY-MM-DD）
    days = sorted({rnd.randint(1, 28) for _ in range(2)})
    if not days:
        days = [1]

    def _pick_date_dir(day: int) -> Path:
        norm = f"2025-12-{day:02d}"
        style = rnd.choice(["ymd", "dot", "cn", "en", "note", "nested"]) 
        if style == "dot":
            return class_dir / f"2025.12.{day:02d}"
        if style == "cn":
            # 允许不补 0：更贴近老师手工输入
            return class_dir / f"2025年12月{day}日"
        if style == "en":
            return class_dir / f"Dec {day:02d} 2025"
        if style == "note":
            return class_dir / f"{norm} 活动_{seed}"
        if style == "nested":
            return class_dir / "2025" / "12" / f"{day:02d}"
        return class_dir / norm

    expected_nonempty = 0

    # 每个日期 1-3 张有效 JPEG + 0-1 个 0 字节坏文件
    # 并且：偶尔为同一天再造一个“同日不同写法”的物理目录，覆盖合并逻辑
    for day in days:
        ddir = _pick_date_dir(day)
        ddir.mkdir(parents=True, exist_ok=True)
        for i in range(rnd.randint(1, 3)):
            name = rnd.choice([
                f"IMG_{seed}_d{day:02d}_{i}.jpg",
                f"课堂照片 {i}（seed={seed}）.jpg",
                f"photo_{i}_space name_{seed}.jpg",
            ])
            write_jpeg(ddir / name, text=f"seed={seed} day={day:02d} i={i}", seed=seed * 1000 + i)
            expected_nonempty += 1

        if rnd.random() < 0.5:
            write_empty_file(ddir / f"bad_{seed}_d{day:02d}.jpg")

        if rnd.random() < 0.35:
            alias = _pick_date_dir(day)
            if alias != ddir:
                alias.mkdir(parents=True, exist_ok=True)
                write_jpeg(alias / f"ALIAS_{seed}_d{day:02d}.jpg", text=f"alias seed={seed} day={day}", seed=seed * 3000 + day)
                expected_nonempty += 1

    # 根目录：放 1-2 张有效照片（模拟老师直接把照片丢进 class_photos/）
    base_mtime = int(time.time()) - 10000 - seed
    for i in range(rnd.randint(1, 2)):
        p = class_dir / f"ROOT_{seed}_{i}.jpg"
        write_jpeg(p, text=f"root seed={seed} i={i}", seed=seed * 2000 + i)
        os.utime(p, (base_mtime + i, base_mtime + i))
        expected_nonempty += 1

    # 平台垃圾文件（应被忽略）
    (class_dir / ".DS_Store").write_text("x", encoding="utf-8")
    (class_dir / "__MACOSX").mkdir(parents=True, exist_ok=True)
    (class_dir / "._IMG_0001.jpg").write_text("x", encoding="utf-8")

    config_path = base / "config.json"
    _write_min_config(config_path)

    return RandomDataset(
        input_dir=input_dir,
        class_dir=class_dir,
        output_dir=output_dir,
        log_dir=log_dir,
        config_path=config_path,
        expected_nonempty_images=expected_nonempty,
    )


@pytest.mark.skipif(not RUN_RANDOM, reason="set SUNDAY_PHOTOS_RUN_RANDOM_TESTS=1 to enable randomized regression")
@pytest.mark.randomized
@pytest.mark.parametrize("seed", [1, 2, 3, 5, 8, 13])
def test_randomized_offline_pipeline_runs_and_is_repeatable(tmp_path: Path, seed: int):
    ds = _build_random_dataset(tmp_path, seed)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir),
        config_file=str(ds.config_path),
    )

    # 1) 首次运行：应成功，并产生输出（全部 unknown）
    assert organizer.run() is True
    unknown_root = ds.output_dir / "unknown_photos"
    assert unknown_root.exists()

    copied = list(unknown_root.rglob("*.jpg"))
    assert len(copied) >= 1

    # 2) 第二次运行：无新增/变更，应仍成功且不崩溃
    assert organizer.run() is True
