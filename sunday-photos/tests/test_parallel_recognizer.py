import os
from unittest.mock import MagicMock

import pytest


def test_parallel_recognize_respects_disable_env(monkeypatch):
    """SUNDAY_PHOTOS_NO_PARALLEL=1 时，不应触发 multiprocessing 代码路径。"""

    from src.core import parallel_recognizer

    monkeypatch.setenv("SUNDAY_PHOTOS_NO_PARALLEL", "1")

    # 如果走到 multiprocessing.get_context，我们让它直接炸，便于断言。
    mp_mock = MagicMock()
    mp_mock.get_context.side_effect = AssertionError("multiprocessing should not be used when disabled")
    monkeypatch.setitem(__import__("sys").modules, "multiprocessing", mp_mock)

    # patch recognize_one，避免依赖 face_recognition
    monkeypatch.setattr(
        parallel_recognizer,
        "recognize_one",
        lambda p: (p, {"status": "no_matches_found", "recognized_students": [], "total_faces": 0}),
    )

    out = list(
        parallel_recognizer.parallel_recognize(
            ["a.jpg", "b.jpg"],
            known_encodings=[],
            known_names=[],
            tolerance=0.6,
            min_face_size=50,
            workers=4,
            chunk_size=2,
        )
    )
    assert [p for p, _ in out] == ["a.jpg", "b.jpg"]


@pytest.mark.parametrize("organizer_import", ["src.core.main", "main"])
def test_core_process_photos_parallel_fallback_to_serial(tmp_path, monkeypatch, organizer_import: str):
    """并行识别异常时，应回退到串行 recognize_faces，保证流程不中断。"""

    if organizer_import == "src.core.main":
        from src.core.main import SimplePhotoOrganizer
        import src.core.main as organizer_module
    else:
        from main import SimplePhotoOrganizer
        import main as organizer_module

    # 造一个日期目录 + 两个非空文件
    input_dir = tmp_path / "input"
    class_dir = input_dir / "class_photos" / "2024-12-21"
    class_dir.mkdir(parents=True, exist_ok=True)
    p1 = class_dir / "a.jpg"
    p2 = class_dir / "b.jpg"
    p1.write_bytes(b"x")
    p2.write_bytes(b"y")

    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    organizer = SimplePhotoOrganizer(input_dir=str(input_dir), output_dir=str(output_dir), log_dir=str(log_dir))
    organizer._organize_input_by_date = lambda: None

    # 强制开启并行配置：min_photos=1
    monkeypatch.setattr(
        organizer_module,
        "ConfigLoader",
        lambda: MagicMock(get_parallel_recognition=lambda: {"enabled": True, "workers": 2, "chunk_size": 1, "min_photos": 1}),
    )

    # 并行入口直接抛异常，触发 fallback
    monkeypatch.setattr(organizer_module, "parallel_recognize", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

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
    assert mock_recognizer.recognize_faces.call_count == 2
