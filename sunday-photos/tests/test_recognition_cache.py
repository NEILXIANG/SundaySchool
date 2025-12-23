import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize("organizer_import", ["src.core.main", "main"])
def test_recognition_cache_hits_second_run(tmp_path: Path, monkeypatch, organizer_import: str):
    """二次运行应命中日期缓存，避免重复调用 recognize_faces。"""

    if organizer_import == "src.core.main":
        from src.core.main import SimplePhotoOrganizer
    else:
        from main import SimplePhotoOrganizer

    input_dir = tmp_path / "input"
    class_dir = input_dir / "class_photos"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    date_dir = class_dir / "2024-12-21"
    date_dir.mkdir(parents=True, exist_ok=True)

    # 写两个非空文件（不需要真实图片内容，因为我们 mock recognize_faces）
    p1 = date_dir / "a.jpg"
    p2 = date_dir / "b.jpg"
    p1.write_bytes(b"not-empty-1")
    p2.write_bytes(b"not-empty-2")

    organizer = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))

    # 避免测试里发生自动移动（本例已按日期放好）
    organizer._organize_input_by_date = lambda: None

    # mock 掉人脸识别，返回固定结构
    mock_recognizer = MagicMock()
    mock_recognizer.tolerance = 0.6
    mock_recognizer.known_encodings = []
    mock_recognizer.known_student_names = []
    mock_recognizer.recognize_faces.side_effect = [
        {"status": "no_matches_found", "message": "", "recognized_students": [], "total_faces": 1, "unknown_faces": 1},
        {"status": "no_matches_found", "message": "", "recognized_students": [], "total_faces": 1, "unknown_faces": 1},
    ]
    organizer.face_recognizer = mock_recognizer

    # 第一次：应调用 2 次，并写入缓存
    organizer.process_photos([str(p1), str(p2)])
    assert mock_recognizer.recognize_faces.call_count == 2

    # 第二次：同文件未变，应 0 次调用（全命中缓存）
    mock_recognizer.recognize_faces.reset_mock()
    organizer.process_photos([str(p1), str(p2)])
    assert mock_recognizer.recognize_faces.call_count == 0


@pytest.mark.parametrize("organizer_import", ["src.core.main", "main"])
def test_deleted_dates_invalidate_cache(tmp_path: Path, organizer_import: str):
    """deleted_dates 应触发日期缓存文件删除。"""

    if organizer_import == "src.core.main":
        from src.core.main import SimplePhotoOrganizer
        from src.core.recognition_cache import date_cache_path, save_date_cache_atomic
    else:
        from main import SimplePhotoOrganizer
        from core.recognition_cache import date_cache_path, save_date_cache_atomic

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    organizer = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))

    # 预先造一个缓存文件
    date = "2024-12-21"
    save_date_cache_atomic(output_dir, date, {"version": 1, "date": date, "params_fingerprint": "x", "entries": {}})
    cache_file = date_cache_path(output_dir, date)
    assert cache_file.exists()

    # 构造一个“仅删除同步”的增量计划，并让 scan_input_directory 不做真实扫描
    class _Plan:
        changed_dates = set()
        deleted_dates = {date}
        snapshot = None

    organizer._incremental_plan = _Plan()
    organizer.scan_input_directory = lambda: []

    organizer.initialized = True
    organizer.initialize = lambda force=False: True

    ok = organizer.run()
    assert ok is True
    assert not cache_file.exists()


@pytest.mark.parametrize("organizer_import", ["src.core.main", "main"])
def test_recognition_cache_invalidates_on_params_change(tmp_path: Path, organizer_import: str):
    """当识别参数（如 tolerance）变化时，应视为缓存失效并重新调用 recognize_faces。"""

    if organizer_import == "src.core.main":
        from src.core.main import SimplePhotoOrganizer
    else:
        from main import SimplePhotoOrganizer

    input_dir = tmp_path / "input"
    class_dir = input_dir / "class_photos"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    date_dir = class_dir / "2024-12-21"
    date_dir.mkdir(parents=True, exist_ok=True)

    p1 = date_dir / "a.jpg"
    p1.write_bytes(b"not-empty-1")

    organizer = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))
    organizer._organize_input_by_date = lambda: None

    mock_recognizer = MagicMock()
    mock_recognizer.tolerance = 0.6
    mock_recognizer.known_encodings = []
    mock_recognizer.known_student_names = []
    mock_recognizer.recognize_faces.return_value = {
        "status": "no_matches_found",
        "message": "",
        "recognized_students": [],
        "total_faces": 1,
        "unknown_faces": 1,
    }
    organizer.face_recognizer = mock_recognizer

    organizer.process_photos([str(p1)])
    assert mock_recognizer.recognize_faces.call_count == 1

    # 变更识别参数：应整体失效（即使文件没变）
    mock_recognizer.recognize_faces.reset_mock()
    mock_recognizer.tolerance = 0.7
    organizer.process_photos([str(p1)])
    assert mock_recognizer.recognize_faces.call_count == 1


@pytest.mark.parametrize("organizer_import", ["src.core.main", "main"])
def test_recognition_cache_prunes_removed_files(tmp_path: Path, organizer_import: str):
    """当某日期文件夹里照片减少时，应在保存缓存时剪枝旧条目，避免缓存无限增长。"""

    if organizer_import == "src.core.main":
        from src.core.main import SimplePhotoOrganizer
        from src.core.recognition_cache import date_cache_path
    else:
        from main import SimplePhotoOrganizer
        from core.recognition_cache import date_cache_path

    input_dir = tmp_path / "input"
    class_dir = input_dir / "class_photos"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    date = "2024-12-21"
    date_dir = class_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)

    p1 = date_dir / "a.jpg"
    p2 = date_dir / "b.jpg"
    p1.write_bytes(b"not-empty-1")
    p2.write_bytes(b"not-empty-2")

    organizer = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))
    organizer._organize_input_by_date = lambda: None

    mock_recognizer = MagicMock()
    mock_recognizer.tolerance = 0.6
    mock_recognizer.known_encodings = []
    mock_recognizer.known_student_names = []
    mock_recognizer.recognize_faces.return_value = {
        "status": "no_matches_found",
        "message": "",
        "recognized_students": [],
        "total_faces": 1,
        "unknown_faces": 1,
    }
    organizer.face_recognizer = mock_recognizer

    organizer.process_photos([str(p1), str(p2)])
    cache_file = date_cache_path(output_dir, date)
    assert cache_file.exists()

    # 只保留 p1：第二轮会保存缓存并剪枝掉 b.jpg
    organizer.process_photos([str(p1)])
    data = __import__("json").loads(cache_file.read_text(encoding="utf-8"))
    entries = data.get("entries") or {}
    assert "2024-12-21/a.jpg" in entries
    assert "2024-12-21/b.jpg" not in entries
