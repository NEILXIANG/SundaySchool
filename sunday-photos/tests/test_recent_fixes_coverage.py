import os
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.mark.parametrize("organizer_import", ["src.core.main", "core.main"])
def test_unknown_face_clustering_disabled_does_not_run(tmp_path, monkeypatch, organizer_import: str):
    if organizer_import == "src.core.main":
        import src.core.main as organizer_module
        from src.core.main import SimplePhotoOrganizer
    else:
        import core.main as organizer_module
        from core.main import SimplePhotoOrganizer

    organizer = SimplePhotoOrganizer(input_dir=str(tmp_path / "input"), output_dir=str(tmp_path / "output"), log_dir=str(tmp_path / "logs"))
    
    # Initialize with proper mocks
    from unittest.mock import MagicMock
    
    organizer.student_manager = MagicMock()
    organizer.face_recognizer = MagicMock()
    organizer.file_organizer = MagicMock()
    organizer.initialized = True

    monkeypatch.setattr(organizer, "scan_input_directory", lambda: ["any.jpg"])
    monkeypatch.setattr(organizer, "_cleanup_output_for_dates", lambda *_args, **_kwargs: None)

    # 模拟：有未知编码，但配置关闭聚类
    monkeypatch.setattr(
        organizer,
        "process_photos",
        lambda _photos: ([], ["u1.jpg"], {"u1.jpg": ["enc1"], "u2.jpg": ["enc2"]}),
    )

    class _Cfg:
        def get_unknown_face_clustering(self):
            return {"enabled": False, "threshold": 0.12, "min_cluster_size": 99}

        def get_tolerance(self):
            return 0.6

        def get_min_face_size(self):
            return 20

        def get_face_backend_engine(self):
            return "insightface"

        def get_parallel_recognition(self):
            return {"enabled": False}

        def get_input_dir(self):
            return "input"

        def get_output_dir(self):
            return "output"

        def get_log_dir(self):
            return "logs"

    # Ensure organizer uses this config (instead of reading repo config.json)
    organizer._config_loader = _Cfg()
    # 如果错误地触发 UnknownClustering，这里会直接失败
    monkeypatch.setattr(
        organizer_module,
        "UnknownClustering",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("UnknownClustering should not be instantiated")),
    )

    captured = {}

    def _organize_output(_recognition_results, _unknown_photos, unknown_clusters):
        captured["unknown_clusters"] = unknown_clusters
        return {}

    monkeypatch.setattr(organizer, "organize_output", _organize_output)

    assert organizer.run() is True
    assert captured["unknown_clusters"] is None


@pytest.mark.parametrize("organizer_import", ["src.core.main", "core.main"])
def test_unknown_face_clustering_enabled_passes_threshold_and_min_cluster_size(tmp_path, monkeypatch, organizer_import: str):
    if organizer_import == "src.core.main":
        import src.core.main as organizer_module
        from src.core.main import SimplePhotoOrganizer
    else:
        import core.main as organizer_module
        from core.main import SimplePhotoOrganizer

    organizer = SimplePhotoOrganizer(input_dir=str(tmp_path / "input"), output_dir=str(tmp_path / "output"), log_dir=str(tmp_path / "logs"))
    
    # Initialize with proper mocks
    from unittest.mock import MagicMock
    
    organizer.student_manager = MagicMock()
    organizer.face_recognizer = MagicMock()
    organizer.file_organizer = MagicMock()
    organizer.initialized = True

    monkeypatch.setattr(organizer, "scan_input_directory", lambda: ["any.jpg"])
    monkeypatch.setattr(organizer, "_cleanup_output_for_dates", lambda *_args, **_kwargs: None)

    # 仅对 unknown_photos 里出现的路径做聚类
    monkeypatch.setattr(
        organizer,
        "process_photos",
        lambda _photos: ([], ["u1.jpg"], {"u1.jpg": ["enc1"], "extra.jpg": ["enc2"]}),
    )

    class _Cfg:
        def get_unknown_face_clustering(self):
            return {"enabled": True, "threshold": 0.33, "min_cluster_size": 3}

        def get_tolerance(self):
            return 0.6

        def get_min_face_size(self):
            return 20

        def get_face_backend_engine(self):
            return "insightface"

        def get_parallel_recognition(self):
            return {"enabled": False}

        def get_input_dir(self):
            return "input"

        def get_output_dir(self):
            return "output"

        def get_log_dir(self):
            return "logs"

    # Ensure organizer uses this config (instead of reading repo config.json)
    organizer._config_loader = _Cfg()
    calls = {"init": None, "add": []}

    class FakeClustering:
        def __init__(self, tolerance: float, min_cluster_size: int):
            calls["init"] = (tolerance, min_cluster_size)

        def add_faces(self, path, encodings):
            calls["add"].append((path, list(encodings)))

        def get_results(self):
            return {"Unknown_Person_1": ["u1.jpg"]}

    monkeypatch.setattr(organizer_module, "UnknownClustering", FakeClustering)

    captured = {}

    def _organize_output(_recognition_results, _unknown_photos, unknown_clusters):
        captured["unknown_clusters"] = unknown_clusters
        return {}

    monkeypatch.setattr(organizer, "organize_output", _organize_output)

    assert organizer.run() is True
    assert calls["init"] == (0.33, 3)
    assert calls["add"] == [("u1.jpg", ["enc1"])], "只应对 unknown_photos 内的路径调用 add_faces"
    assert captured["unknown_clusters"] == {"Unknown_Person_1": ["u1.jpg"]}


def test_config_loader_reads_face_recognition_compat_fields(tmp_path):
    from src.core.config_loader import ConfigLoader

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "face_recognition": {"tolerance": 0.55, "min_face_size": 77},
                "unknown_face_clustering": {"enabled": "yes", "threshold": "0.40", "min_cluster_size": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    loader = ConfigLoader(config_file=str(cfg_path), base_dir=tmp_path)

    assert loader.get_tolerance() == 0.55
    assert loader.get_min_face_size() == 77

    # unknown_face_clustering：enabled 做 bool 归一；min_cluster_size 至少为 1
    uc = loader.get_unknown_face_clustering()
    assert uc["enabled"] is True
    assert uc["threshold"] == 0.40
    assert uc["min_cluster_size"] == 1


def test_cli_no_parallel_sets_env_var(monkeypatch):
    # 通过 --check-env 提前返回，避免跑完整主流程
    from src.cli import run as cli_run

    monkeypatch.delenv("SUNDAY_PHOTOS_NO_PARALLEL", raising=False)
    monkeypatch.setattr(cli_run, "check_environment", lambda: True)
    monkeypatch.setattr(sys, "argv", ["prog", "--no-parallel", "--check-env"])

    cli_run.main()
    assert os.environ.get("SUNDAY_PHOTOS_NO_PARALLEL") == "1"
