import json
import os
import sys
import types
from pathlib import Path


def _write_minimal_png(path: Path) -> None:
    # A valid 1x1 transparent PNG.
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000A49444154789C6360000002000154AEE2E50000000049454E44AE426082"
        )
    )


def _install_dummy_face_recognizer_module(monkeypatch):
    """Install a dummy src.core.face_recognizer module to avoid importing heavy deps.

    We only need FaceRecognizer signature + attributes for core.main.initialize() tests.
    """

    dummy = types.ModuleType("src.core.face_recognizer")

    class DummyFaceRecognizer:
        def __init__(self, student_manager, tolerance=None, min_face_size=None, log_dir=None):
            self.student_manager = student_manager
            self.tolerance = tolerance
            self.min_face_size = int(min_face_size) if min_face_size is not None else None

            # Optional; exists to mirror the production interface.
            self.log_dir = log_dir

    dummy.FaceRecognizer = DummyFaceRecognizer
    monkeypatch.setitem(sys.modules, "src.core.face_recognizer", dummy)


def test_config_loader_unified_params_supports_legacy_face_recognition_block(tmp_path: Path):
    """tolerance/min_face_size 在 config.json 中应统一读取，且兼容 face_recognition.* 老字段。"""

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"face_recognition": {"tolerance": 0.42, "min_face_size": 123}}),
        encoding="utf-8",
    )

    from src.core.config_loader import ConfigLoader

    cfg = ConfigLoader(config_file=cfg_path, base_dir=tmp_path)
    assert cfg.get_tolerance() == 0.42
    assert cfg.get_min_face_size() == 123


def test_initialize_passes_unified_params_and_sets_backend_env_from_config(monkeypatch, tmp_path: Path):
    """core 初始化应把统一参数传给 FaceRecognizer，并在未设置 env 时从 config 写入后端 env。"""

    _install_dummy_face_recognizer_module(monkeypatch)

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"
    alice_dir = input_dir / "student_photos" / "Alice"
    alice_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_png(alice_dir / "ref.png")
    (input_dir / "class_photos").mkdir(parents=True, exist_ok=True)

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "tolerance": 0.55,
                "min_face_size": 111,
                "face_backend": {"engine": "dlib"},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("SUNDAY_PHOTOS_FACE_BACKEND", raising=False)

    from src.core.main import SimplePhotoOrganizer

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        config_file=str(cfg_path),
    )

    assert organizer.initialize() is True
    assert getattr(organizer.face_recognizer, "tolerance") == 0.55
    assert getattr(organizer.face_recognizer, "min_face_size") == 111
    assert os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND") == "dlib"


def test_initialize_does_not_override_backend_env(monkeypatch, tmp_path: Path):
    """若用户已设置 SUNDAY_PHOTOS_FACE_BACKEND，则 core 初始化不得覆盖。"""

    _install_dummy_face_recognizer_module(monkeypatch)

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"
    alice_dir = input_dir / "student_photos" / "Alice"
    alice_dir.mkdir(parents=True, exist_ok=True)
    _write_minimal_png(alice_dir / "ref.png")
    (input_dir / "class_photos").mkdir(parents=True, exist_ok=True)

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"face_backend": {"engine": "dlib"}, "tolerance": 0.6, "min_face_size": 80}),
        encoding="utf-8",
    )

    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "insightface")

    from src.core.main import SimplePhotoOrganizer

    organizer = SimplePhotoOrganizer(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        log_dir=str(log_dir),
        config_file=str(cfg_path),
    )

    assert organizer.initialize() is True
    assert os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND") == "insightface"
