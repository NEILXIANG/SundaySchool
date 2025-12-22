#!/usr/bin/env python3
"""增量处理（方案1：隐藏状态快照）测试

目标：
- 以 input/class_photos 下的“日期文件夹”为粒度做增量
- 只处理新增/变更日期文件夹
- 删除日期文件夹会同步清理 output 中对应日期目录

说明：本测试不依赖真实人脸识别，专注验证快照 diff 与输出清理策略。
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))
os.chdir(PROJECT_ROOT)

sys.path.insert(0, str(PROJECT_ROOT))

from tests.testdata_builder import write_empty_file, write_jpeg  # noqa: E402


def _touch(path: Path, content: bytes = b""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_snapshot_diff_and_cleanup():
    print("=== 增量处理测试：快照diff与输出清理 ===")

    from incremental_state import (
        build_class_photos_snapshot,
        compute_incremental_plan,
        save_snapshot,
    )
    from main import SimplePhotoOrganizer

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        input_dir = base / "input"
        class_dir = input_dir / "class_photos"
        output_dir = base / "output"
        log_dir = base / "logs"

        # 构造两天照片（真实JPEG），并混入一个空文件（应被快照/扫描忽略）
        write_jpeg(class_dir / "2024-12-21" / "a.jpg", text="2024-12-21 a", seed=1)
        write_jpeg(class_dir / "2024-12-21" / "b.jpg", text="2024-12-21 b", seed=2)
        write_jpeg(class_dir / "2024-12-28" / "c.jpg", text="2024-12-28 c", seed=3)
        write_empty_file(class_dir / "2024-12-21" / "empty.jpg")

        organizer = SimplePhotoOrganizer(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            log_dir=str(log_dir),
        )

        # 避免测试里发生自动移动（本例已按日期放好）
        organizer._organize_input_by_date = lambda: None

        # 首次：无快照，应该认为两个日期都 changed
        prev = None
        cur = build_class_photos_snapshot(class_dir)
        plan = compute_incremental_plan(prev, cur)
        assert plan.changed_dates == {"2024-12-21", "2024-12-28"}
        assert plan.deleted_dates == set()

        # 保存快照，模拟“已成功跑过一次”
        save_snapshot(output_dir, cur)

        # 再次扫描：无变化 => changed_dates 为空，且返回照片列表为空
        photo_files = organizer.scan_input_directory()
        plan2 = organizer._incremental_plan
        assert plan2 is not None
        assert plan2.changed_dates == set()
        assert plan2.deleted_dates == set()
        assert photo_files == []

        # 新增一张照片到 2024-12-28：只应标记这一日 changed
        write_jpeg(class_dir / "2024-12-28" / "new.jpg", text="2024-12-28 new", seed=4)
        photo_files = organizer.scan_input_directory()
        plan3 = organizer._incremental_plan
        assert plan3 is not None
        assert plan3.changed_dates == {"2024-12-28"}
        assert plan3.deleted_dates == set()
        assert any(p.endswith(os.path.join("2024-12-28", "new.jpg")) for p in photo_files)

        # 验证删除同步清理：先构造输出目录里各学生的日期目录（真实JPEG）
        write_jpeg(output_dir / "StudentA" / "2024-12-21" / "x.jpg", text="out x", seed=10)
        write_jpeg(output_dir / "StudentB" / "2024-12-21" / "y.jpg", text="out y", seed=11)
        write_jpeg(output_dir / "unknown_photos" / "2024-12-21" / "z.jpg", text="out z", seed=12)

        # 删除输入中的 2024-12-21
        shutil.rmtree(class_dir / "2024-12-21")
        organizer.scan_input_directory()
        plan4 = organizer._incremental_plan
        assert plan4 is not None
        assert plan4.deleted_dates == {"2024-12-21"}

        # 执行清理（与 run() 中一致）
        organizer._cleanup_output_for_dates(sorted(plan4.deleted_dates))

        assert not (output_dir / "StudentA" / "2024-12-21").exists()
        assert not (output_dir / "StudentB" / "2024-12-21").exists()
        assert not (output_dir / "unknown_photos" / "2024-12-21").exists()

    print("✓ 增量处理测试通过")
    return True


def main():
    ok = True
    try:
        ok = bool(test_snapshot_diff_and_cleanup()) and ok
    except AssertionError as e:
        print(f"✗ 断言失败: {e}")
        ok = False
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        ok = False

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
