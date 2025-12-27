import json
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Canonical import path is src.* (project root must be on sys.path)
sys.path.insert(0, str(PROJECT_ROOT))


def test_console_launcher_creates_top_level_config_and_passes_config_file(tmp_path, monkeypatch):
    # 使用 tmp_path 模拟“程序可写的工作目录”
    import src.cli.console_launcher as cl

    # 新口径：工作目录默认跟随程序所在位置；测试中用 env 覆盖，避免写入真实用户目录
    monkeypatch.setenv("SUNDAY_PHOTOS_WORK_DIR", str(tmp_path / "workdir"))

    organizer = cl.ConsolePhotoOrganizer()
    assert organizer.setup_directories() is True

    captured = {"organizer_init": None, "cfg_loader_path": None, "organizer_obj": None}

    class FakeFaceRecognizer:
        def __init__(self):
            self.tolerance = None
            self.min_face_size = None

    class FakeOrganizer:
        def __init__(self, *args, **kwargs):
            captured["organizer_init"] = dict(kwargs)
            captured["organizer_obj"] = self
            self.face_recognizer = FakeFaceRecognizer()
            self.last_run_report = {
                "organize_stats": {"copied": 0, "failed": 0, "students": {}},
                "pipeline_stats": {"total_photos": 0, "unknown_photos": 0, "students_detected": []},
            }

        def initialize(self):
            return True

        def run(self):
            return True

    class FakeConfigLoader:
        def __init__(self, path):
            captured["cfg_loader_path"] = path

        def get_tolerance(self):
            return 0.51

        def get_min_face_size(self):
            return 88

    fake_core_main = types.ModuleType("src.core.main")
    fake_core_main.SimplePhotoOrganizer = FakeOrganizer
    fake_core_config_loader = types.ModuleType("src.core.config_loader")
    fake_core_config_loader.ConfigLoader = FakeConfigLoader

    monkeypatch.setitem(sys.modules, "src.core.main", fake_core_main)
    monkeypatch.setitem(sys.modules, "src.core.config_loader", fake_core_config_loader)
    monkeypatch.setattr(organizer, "_try_open_folder", lambda *_args, **_kwargs: True)

    assert organizer.process_photos() is True

    # 1) 确认 config.json 被创建，且是顶层口径（与 core/config_loader.py 读取一致）
    config_path = organizer.app_directory / "config.json"
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "tolerance" in data
    assert "min_face_size" in data
    assert "parallel_recognition" in data
    assert "unknown_face_clustering" in data

    # 2) 确认 config_file 参数向下传递到 SimplePhotoOrganizer
    assert captured["organizer_init"]["config_file"] == str(config_path)
    assert captured["cfg_loader_path"] == str(config_path)

    # 3) 确认 tolerance/min_face_size 应用到 face_recognizer（来自 ConfigLoader）
    assert captured["organizer_obj"] is not None
    assert captured["organizer_obj"].face_recognizer.tolerance == 0.51
    assert captured["organizer_obj"].face_recognizer.min_face_size == 88
