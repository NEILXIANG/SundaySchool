#!/usr/bin/env python3
"""大规模测试数据自动构建与运行验证

需求覆盖：
- 自动构建 >10 个学生（student_photos）
- 自动构建 >10 个日期（class_photos/YYYY-MM-DD/）
- 自动构建课堂照片与未知照片
- 不依赖真实人脸识别（避免 face_recognition 计算/失败），聚焦：
  - 增量快照 diff（新增/变更/删除）
  - 输出目录清理策略（按日期清理）
  - FileOrganizer 复制组织输出（学生/日期/文件）
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

from tests.testdata_builder import build_dataset  # noqa: E402


def _count_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for p in directory.rglob('*') if p.is_file())


def test_large_dataset_incremental_and_organize():
    print("=== 大规模数据构建测试：>10学生、>10日期 ===")

    from incremental_state import (
        build_class_photos_snapshot,
        compute_incremental_plan,
        load_snapshot,
        save_snapshot,
    )
    from file_organizer import FileOrganizer
    from main import SimplePhotoOrganizer

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        dataset = build_dataset(
            base,
            student_count=12,
            date_prefix="2025-12",
            date_start_day=1,
            date_count=12,
            photos_per_date=6,
            unknown_per_date=1,
            empty_file_ratio=0.05,
            seed=20251222,
        )
        input_dir = dataset.input_dir
        class_dir = dataset.class_dir
        output_dir = dataset.output_dir
        log_dir = dataset.log_dir
        student_names = dataset.student_names
        dates = dataset.dates

        # 收集“非空”的课堂照片（空文件会被扫描逻辑忽略，这里也不用于模拟识别）
        all_photos = sorted(
            [p for p in class_dir.rglob("*.jpg") if p.is_file() and p.stat().st_size > 0 and p.name.startswith("photo_")]
        )

        # 3) 增量快照：首次 run 应全部认为 changed
        prev = load_snapshot(output_dir)
        assert prev is None, "预期首次运行快照为空"
        cur = build_class_photos_snapshot(class_dir)
        plan1 = compute_incremental_plan(prev, cur)
        assert len(plan1.changed_dates) == len(dates), f"首次变更日期数不符合: {plan1.changed_dates}"
        assert plan1.deleted_dates == set(), f"首次不应有删除日期: {plan1.deleted_dates}"
        save_snapshot(output_dir, cur)

        # 4) 再次无变化：changed_dates 为空
        prev2 = load_snapshot(output_dir)
        cur2 = build_class_photos_snapshot(class_dir)
        plan2 = compute_incremental_plan(prev2, cur2)
        assert plan2.changed_dates == set(), f"无变化时 changed_dates 应为空: {plan2.changed_dates}"
        assert plan2.deleted_dates == set(), f"无变化时 deleted_dates 应为空: {plan2.deleted_dates}"

        # 5) 变更一个日期：新增一张照片
        changed_date = dates[5]
        from tests.testdata_builder import write_jpeg

        write_jpeg(class_dir / changed_date / "extra.jpg", text=f"date={changed_date} extra", seed=999)
        cur3 = build_class_photos_snapshot(class_dir)
        plan3 = compute_incremental_plan(cur2, cur3)
        assert plan3.changed_dates == {changed_date}, f"变更日期识别不正确: {plan3.changed_dates}"

        # 6) FileOrganizer：用“模拟识别结果”组织输出
        organizer = FileOrganizer(str(output_dir))

        recognition_results = {}
        unknown_photos = []

        # 每张照片映射到 2 个学生（确定性分配）
        for i, photo in enumerate(all_photos):
            s1 = student_names[i % len(student_names)]
            s2 = student_names[(i + 1) % len(student_names)]
            if photo.exists():
                recognition_results[str(photo)] = [s1, s2]

        # 每个日期放 1 张未知（仅使用非空文件）
        for date in dates:
            unknown = class_dir / date / "unknown_01.jpg"
            if unknown.exists() and unknown.stat().st_size > 0:
                unknown_photos.append(str(unknown))

        stats = organizer.organize_photos(str(class_dir), recognition_results, unknown_photos)
        print(f"复制任务统计: total={stats['total']} copied={stats['copied']} failed={stats['failed']} skipped={stats.get('skipped', 0)}")
        assert stats["total"] > 10, f"复制任务数过少: {stats}"
        assert stats["copied"] == stats["total"], f"成功复制数不等于总任务数: {stats}"
        assert stats["failed"] == 0, f"复制失败数不为0: {stats}"

        # 验证输出结构：至少应产生学生/日期目录
        for name in student_names:
            student_out = output_dir / name
            assert student_out.exists(), f"学生输出目录不存在: {student_out}"

        # unknown_photos 目录也应该存在（如果有未知照片）
        assert (output_dir / "unknown_photos").exists(), "unknown_photos 输出目录不存在"

        # 7) 删除一个日期文件夹，并验证增量 diff 会识别为 deleted
        deleted_date = dates[2]
        shutil.rmtree(class_dir / deleted_date)
        cur4 = build_class_photos_snapshot(class_dir)
        plan4 = compute_incremental_plan(cur3, cur4)
        assert deleted_date in plan4.deleted_dates, f"删除日期未识别: {plan4.deleted_dates}"

        # 8) 验证清理策略：按日期清理 output 下所有顶层目录的该日期
        app = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))
        app._cleanup_output_for_dates([deleted_date])

        # 该日期在任何学生/unknown 下都不应再存在
        for top in output_dir.iterdir():
            if top.is_dir():
                assert not (top / deleted_date).exists(), f"未清理干净: {top / deleted_date}"

        # 额外：确认确实生成了不少文件（规模验证）
        produced = _count_files(output_dir)
        print(f"输出文件总数(清理后): {produced}")
        assert produced >= 50, f"输出文件数过少(清理后): {produced}"

    print("✓ 大规模数据自动构建与验证通过")
    return True


def main():
    ok = True
    try:
        ok = bool(test_large_dataset_incremental_and_organize()) and ok
    except AssertionError as e:
        print(f"✗ 断言失败: {e}")
        ok = False
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        ok = False

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
