import json
from pathlib import Path


def test_console_launcher_generated_config_includes_face_backend(tmp_path: Path):
    """打包入口自动生成的 config.json 应显式包含 face_backend.engine。

    目的：确保老师端零配置运行时，后端选择是明确的，并且与文档口径一致。
    """

    from src.cli.console_launcher import ConsolePhotoOrganizer

    org = ConsolePhotoOrganizer()
    # Force work directory to a temp folder to avoid touching real release_console.
    org.app_directory = tmp_path

    cfg_path, created = org.create_config_file()
    assert created is True
    data = json.loads(Path(cfg_path).read_text(encoding="utf-8"))

    assert "face_backend" in data
    assert isinstance(data["face_backend"], dict)
    assert data["face_backend"].get("engine") == "insightface"

    # Still keeps unified top-level parameters
    assert data.get("tolerance") == 0.6
    assert data.get("min_face_size") == 50
    assert data.get("parallel_recognition", {}).get("workers") == 6
