import importlib
import json
import multiprocessing as mp
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _child_report_backend(conn):
    """Run inside spawned process; report selected backend and compat class."""
    import os
    import importlib

    # Child is a fresh interpreter under spawn; import-time backend init will run here.
    mod = importlib.import_module("src.core.face_recognizer")
    mod = importlib.reload(mod)

    env_raw = os.environ.get("SUNDAY_PHOTOS_FACE_BACKEND", "")
    selected = mod._get_selected_face_backend_engine()
    cls = None
    if getattr(mod, "face_recognition", None) is not None:
        cls = mod.face_recognition.__class__.__name__
    conn.send({"env": env_raw, "selected": selected, "class": cls})
    conn.close()


def _reload_face_recognizer_module():
    # 重要：face backend 在模块导入时初始化（module-level singleton）。
    # 测试切换后端时必须 reload 才能生效。
    mod = importlib.import_module("src.core.face_recognizer")
    return importlib.reload(mod)


def _make_fr(monkeypatch, tmp_path: Path):
    fr_module = _reload_face_recognizer_module()
    monkeypatch.setattr(fr_module.FaceRecognizer, "load_student_encodings", lambda self: None)
    sm = MagicMock()
    sm.input_dir = tmp_path
    return fr_module.FaceRecognizer(sm), fr_module


def test_config_loader_face_backend_env_overrides_config(monkeypatch, tmp_path: Path):
    from src.core.config_loader import ConfigLoader

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"face_backend": {"engine": "insightface"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "dlib")
    cl = ConfigLoader(config_file=str(cfg_path), base_dir=tmp_path)
    assert cl.get_face_backend_engine() == "dlib"


def test_config_loader_face_backend_from_config_when_no_env(monkeypatch, tmp_path: Path):
    from src.core.config_loader import ConfigLoader

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"face_backend": {"engine": "dlib"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.delenv("SUNDAY_PHOTOS_FACE_BACKEND", raising=False)
    cl = ConfigLoader(config_file=str(cfg_path), base_dir=tmp_path)
    assert cl.get_face_backend_engine() == "dlib"


def test_reference_cache_paths_are_isolated_by_backend(monkeypatch, tmp_path: Path):
    # InsightFace paths
    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "insightface")
    monkeypatch.delenv("SUNDAY_PHOTOS_INSIGHTFACE_MODEL", raising=False)
    fr1, _mod1 = _make_fr(monkeypatch, tmp_path)
    assert fr1._ref_cache_dir.as_posix().endswith("/logs/reference_encodings/insightface/buffalo_l")
    assert fr1._ref_snapshot_path.as_posix().endswith("/logs/reference_index/insightface/buffalo_l.json")

    # dlib/face_recognition paths
    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "dlib")
    fr2, _mod2 = _make_fr(monkeypatch, tmp_path)
    assert fr2._ref_cache_dir.as_posix().endswith("/logs/reference_encodings/dlib/face_recognition")
    assert fr2._ref_snapshot_path.as_posix().endswith("/logs/reference_index/dlib/face_recognition.json")

    # Ensure they are different locations (avoid cross-engine cache pollution)
    assert fr1._ref_cache_dir != fr2._ref_cache_dir
    assert fr1._ref_snapshot_path != fr2._ref_snapshot_path


def test_spawn_child_inherits_face_backend_env(monkeypatch, tmp_path: Path):
    # Use dlib backend in test to avoid heavy InsightFace model init in child.
    # In tests, face_recognition is a lightweight stub module, so import is fast.
    monkeypatch.setenv("SUNDAY_PHOTOS_FACE_BACKEND", "dlib")

    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_child_report_backend, args=(child_conn,))
    p.start()

    try:
        assert parent_conn.poll(10.0), "child did not respond in time"
        payload = parent_conn.recv()
    finally:
        p.join(timeout=10.0)
        if p.is_alive():
            p.terminate()
            p.join(timeout=5.0)

    assert payload["selected"] == "dlib"
    # Ensure the child actually initialized the expected compat layer
    assert payload["class"] == "_DlibFaceRecognitionCompat"
