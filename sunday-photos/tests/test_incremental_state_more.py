import os
import time
from pathlib import Path

from src.core.incremental_state import build_class_photos_snapshot, compute_incremental_plan
from tests.testdata_builder import write_jpeg


def test_incremental_plan_detects_added_changed_deleted(tmp_path: Path):
    class_dir = tmp_path / "input" / "class_photos"

    # 初始：A、B
    a = class_dir / "2025-12-21"
    b = class_dir / "2025-12-22"
    write_jpeg(a / "a1.jpg", text="A1", seed=1)
    write_jpeg(b / "b1.jpg", text="B1", seed=2)

    prev = build_class_photos_snapshot(class_dir)

    # 变更：删除 A；修改 B（mtime/内容变化）；新增 C
    # 删除 A
    for p in a.rglob("*"):
        if p.is_file():
            p.unlink()
    a.rmdir()

    # 修改 B：更新 mtime
    b1 = b / "b1.jpg"
    prev_mtime = int(b1.stat().st_mtime)
    new_mtime = max(int(time.time()), prev_mtime + 10)
    os.utime(b1, (new_mtime, new_mtime))

    # 新增 C
    c = class_dir / "2025-12-23"
    write_jpeg(c / "c1.jpg", text="C1", seed=3)

    cur = build_class_photos_snapshot(class_dir)
    plan = compute_incremental_plan(prev, cur)

    assert plan.deleted_dates == {"2025-12-21"}
    assert "2025-12-22" in plan.changed_dates
    assert "2025-12-23" in plan.changed_dates


def test_snapshot_ignores_zero_byte_images(tmp_path: Path):
    class_dir = tmp_path / "input" / "class_photos" / "2025-12-21"
    class_dir.mkdir(parents=True, exist_ok=True)

    # 0 字节文件应被忽略
    bad = class_dir / "bad.jpg"
    bad.write_bytes(b"")

    snap = build_class_photos_snapshot(tmp_path / "input" / "class_photos")
    files = snap["dates"]["2025-12-21"]["files"]
    assert files == []
