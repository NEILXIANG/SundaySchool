import json
from pathlib import Path


def test_cli_backend_detection_env_overrides_config(monkeypatch, tmp_path: Path):
    """src/cli/run.py 环境检查应遵循 env > config 的后端选择优先级。"""

    # Arrange: create a config.json that selects dlib
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"face_backend": {"engine": "dlib"}}), encoding="utf-8")

    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "insightface")

    import importlib

    cli_run = importlib.import_module("src.cli.run")

    import src.core.config as core_config
    monkeypatch.setattr(core_config, "CONFIG_FILE_PATH", cfg_path)
    cli_run = importlib.reload(cli_run)

    assert cli_run._get_backend_engine_from_env_or_config() == "insightface"


def test_cli_backend_detection_reads_config_when_no_env(monkeypatch, tmp_path: Path):
    """未设置 env 时，src/cli/run.py 环境检查应读取 config.json 的 face_backend.engine。"""

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"face_backend": {"engine": "dlib"}}), encoding="utf-8")

    monkeypatch.delenv("SUNDAY_PHOTOS_FACE_BACKEND", raising=False)

    import importlib

    cli_run = importlib.import_module("src.cli.run")

    import src.core.config as core_config
    monkeypatch.setattr(core_config, "CONFIG_FILE_PATH", cfg_path)
    cli_run = importlib.reload(cli_run)

    assert cli_run._get_backend_engine_from_env_or_config() == "dlib"


def test_cli_backend_detection_invalid_config_falls_back(monkeypatch, tmp_path: Path):
    """配置值异常时应回退默认 insightface（避免 check-env 因配置损坏而崩）。"""

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"face_backend": {"engine": "UNKNOWN"}}), encoding="utf-8")

    monkeypatch.delenv("SUNDAY_PHOTOS_FACE_BACKEND", raising=False)

    import importlib

    cli_run = importlib.import_module("src.cli.run")

    import src.core.config as core_config
    monkeypatch.setattr(core_config, "CONFIG_FILE_PATH", cfg_path)
    cli_run = importlib.reload(cli_run)

    assert cli_run._get_backend_engine_from_env_or_config() == "insightface"
