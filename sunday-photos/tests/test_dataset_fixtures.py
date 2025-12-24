from pathlib import Path


def test_offline_generated_dataset_structure(offline_generated_dataset):
    ds = offline_generated_dataset
    assert ds.input_dir.exists()
    assert (ds.input_dir / "student_photos").exists()
    assert (ds.input_dir / "class_photos").exists()

    # 至少包含两个日期目录
    for date in ds.dates:
        d = ds.class_dir / date
        assert d.exists() and d.is_dir()

    # 学生目录存在
    for name in ds.student_names:
        assert (ds.student_dir / name).exists()

    # 输出与日志目录存在
    assert ds.output_dir.exists()
    assert ds.log_dir.exists()


def test_fixture_paths_are_under_tmp(tmp_path: Path, offline_generated_dataset):
    ds = offline_generated_dataset
    assert str(ds.input_dir).startswith(str(tmp_path))
    assert str(ds.output_dir).startswith(str(tmp_path))
    assert str(ds.log_dir).startswith(str(tmp_path))
