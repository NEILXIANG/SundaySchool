import json
import os
from pathlib import Path

import numpy as np


def test_reference_cache_paths_follow_log_dir_and_fallback(tmp_path: Path, monkeypatch):
    """Reference cache/snapshot paths should follow log_dir when provided, else fall back to input_dir/logs."""

    from src.core.face_recognizer import FaceRecognizer

    class DummyStudentManager:
        def __init__(self, input_dir: Path):
            self.input_dir = str(input_dir)

    fr = FaceRecognizer.__new__(FaceRecognizer)
    fr.student_manager = DummyStudentManager(tmp_path / "input")
    fr._backend_engine = "insightface"
    fr._backend_model = "buffalo l"  # contains space to verify safe keying

    # Case 1: explicit log_dir
    fr._log_dir = tmp_path / "logs"
    cache_dir = fr._resolve_ref_cache_dir()
    snap_path = fr._resolve_ref_snapshot_path()

    assert cache_dir == tmp_path / "logs" / "reference_encodings" / "insightface" / "buffalo_l"
    assert snap_path == tmp_path / "logs" / "reference_index" / "insightface" / "buffalo_l.json"

    # Case 2: no log_dir -> legacy fallback under input_dir/logs
    fr._log_dir = None
    cache_dir2 = fr._resolve_ref_cache_dir()
    snap_path2 = fr._resolve_ref_snapshot_path()

    assert cache_dir2 == tmp_path / "input" / "logs" / "reference_encodings" / "insightface" / "buffalo_l"
    assert snap_path2 == tmp_path / "input" / "logs" / "reference_index" / "insightface" / "buffalo_l.json"


def test_recognition_cache_store_result_sanitizes_numpy_and_is_json_writable(tmp_path: Path):
    """Recognition cache must sanitize numpy values so cache can be saved as JSON."""

    from src.core.recognition_cache import (
        CacheKey,
        compute_params_fingerprint,
        load_date_cache,
        normalize_cache_for_fingerprint,
        save_date_cache_atomic,
        store_result,
    )

    output_dir = tmp_path / "output"
    date = "2025-12-27"

    params_fp = compute_params_fingerprint({"tolerance": 0.6, "min_face_size": 50})
    cache = normalize_cache_for_fingerprint(load_date_cache(output_dir, date), date, params_fp)

    key = CacheKey(date=date, rel_path="IMG_001.jpg", size=123, mtime=456)
    result = {
        "status": "success",
        "recognized_students": ["Alice"],
        "unknown_encodings": [np.asarray([1.0, 2.0, 3.0], dtype=np.float32)],
    }

    store_result(cache, key, result)
    save_date_cache_atomic(output_dir, date, cache)

    # Should be valid JSON and contain a list instead of numpy ndarray
    p = output_dir / ".state" / "recognition_cache_by_date" / f"{date}.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    stored = data["entries"]["IMG_001.jpg"]["result"]["unknown_encodings"][0]
    assert stored == [1.0, 2.0, 3.0]


def test_parallel_recognizer_caps_chunksize_and_respects_env_disable(monkeypatch):
    """parallel_recognize caps chunksize to <=2 and must not spawn when SUNDAY_PHOTOS_NO_PARALLEL=1."""

    from src.core import parallel_recognizer as pr

    # Patch recognize_one to avoid importing heavy face backends.
    def fake_recognize_one(p: str):
        return p, {"status": "ok", "recognized_students": [], "total_faces": 0}

    monkeypatch.setattr(pr, "recognize_one", fake_recognize_one)

    # ---- chunksize cap path (parallel enabled) ----
    import multiprocessing

    seen = {"chunksize": None, "pool_used": False}

    class FakePool:
        def __init__(self, *args, **kwargs):
            seen["pool_used"] = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def imap_unordered(self, func, iterable, *, chunksize=1):
            seen["chunksize"] = chunksize
            for item in iterable:
                yield func(item)

    class FakeCtx:
        def Pool(self, *args, **kwargs):
            return FakePool(*args, **kwargs)

    def fake_get_context(method: str):
        assert method == "spawn"
        return FakeCtx()

    monkeypatch.delenv("SUNDAY_PHOTOS_NO_PARALLEL", raising=False)
    monkeypatch.setattr(multiprocessing, "get_context", fake_get_context)

    out = list(
        pr.parallel_recognize(
            ["a.jpg", "b.jpg", "c.jpg"],
            known_encodings=[],
            known_names=[],
            tolerance=0.6,
            min_face_size=50,
            workers=4,
            chunk_size=99,
        )
    )
    assert seen["pool_used"] is True
    assert seen["chunksize"] == 2
    assert [p for (p, _d) in out] == ["a.jpg", "b.jpg", "c.jpg"]

    # ---- env disable path (must not call multiprocessing.get_context) ----
    def bomb_get_context(_method: str):
        raise AssertionError("multiprocessing.get_context should not be called when SUNDAY_PHOTOS_NO_PARALLEL=1")

    monkeypatch.setenv("SUNDAY_PHOTOS_NO_PARALLEL", "1")
    monkeypatch.setattr(multiprocessing, "get_context", bomb_get_context)

    out2 = list(
        pr.parallel_recognize(
            ["x.jpg", "y.jpg"],
            known_encodings=[],
            known_names=[],
            tolerance=0.6,
            min_face_size=50,
            workers=4,
            chunk_size=99,
        )
    )
    assert [p for (p, _d) in out2] == ["x.jpg", "y.jpg"]


def test_work_root_dir_prefers_env_override(tmp_path: Path, monkeypatch):
    """SUNDAY_PHOTOS_WORK_DIR should force the chosen work root directory."""

    from src.core import platform_paths as pp

    custom = tmp_path / "custom_work_root"
    monkeypatch.setenv("SUNDAY_PHOTOS_WORK_DIR", str(custom))
    assert pp.get_default_work_root_dir() == custom


def test_work_root_dir_candidate_priority(tmp_path: Path, monkeypatch):
    """When no env override, work root should be picked by priority among candidates."""

    from src.core import platform_paths as pp

    monkeypatch.delenv("SUNDAY_PHOTOS_WORK_DIR", raising=False)

    program = tmp_path / "program"
    desktop = tmp_path / "desktop"
    home = tmp_path / "home"
    program.mkdir()
    desktop.mkdir()
    home.mkdir()

    monkeypatch.setattr(pp, "get_program_dir", lambda: program)
    monkeypatch.setattr(pp, "get_desktop_dir", lambda: desktop)
    monkeypatch.setattr(pp.Path, "home", classmethod(lambda cls: home))

    # Only desktop is writable.
    monkeypatch.setattr(pp, "_is_writable_dir", lambda p: Path(p) == desktop)
    assert pp.get_default_work_root_dir() == desktop

    # None are writable -> returns the first candidate (program dir) as best-effort.
    monkeypatch.setattr(pp, "_is_writable_dir", lambda _p: False)
    assert pp.get_default_work_root_dir() == program


def test_params_fingerprint_changes_with_reference_fingerprint_and_is_order_stable():
    """reference_fingerprint must participate in params_fingerprint; key order should not matter."""

    from src.core.recognition_cache import compute_params_fingerprint

    fp_a = compute_params_fingerprint(
        {"tolerance": 0.6, "min_face_size": 50, "reference_fingerprint": "aaa"}
    )
    fp_b = compute_params_fingerprint(
        {"min_face_size": 50, "reference_fingerprint": "bbb", "tolerance": 0.6}
    )
    fp_a_reordered = compute_params_fingerprint(
        {"reference_fingerprint": "aaa", "min_face_size": 50, "tolerance": 0.6}
    )

    assert fp_a != fp_b
    assert fp_a == fp_a_reordered


def test_date_cache_roundtrip_and_invalidate_on_fingerprint_mismatch(tmp_path: Path):
    """Small integration test: save cache -> load -> fingerprint mismatch resets entries."""

    from src.core.recognition_cache import (
        CacheKey,
        compute_params_fingerprint,
        load_date_cache,
        lookup_result,
        normalize_cache_for_fingerprint,
        save_date_cache_atomic,
        store_result,
    )

    output_dir = tmp_path / "output"
    date = "2025-12-27"

    fp1 = compute_params_fingerprint({"tolerance": 0.6, "min_face_size": 50, "reference_fingerprint": "r1"})
    cache = normalize_cache_for_fingerprint(load_date_cache(output_dir, date), date, fp1)

    key = CacheKey(date=date, rel_path="A.jpg", size=1, mtime=2)
    store_result(cache, key, {"status": "success", "recognized_students": ["Alice"], "total_faces": 1})
    save_date_cache_atomic(output_dir, date, cache)

    loaded = load_date_cache(output_dir, date)
    assert lookup_result(loaded, key) is not None

    # Now simulate params change (e.g., reference_fingerprint changed) -> entries should reset.
    fp2 = compute_params_fingerprint({"tolerance": 0.6, "min_face_size": 50, "reference_fingerprint": "r2"})
    normalized = normalize_cache_for_fingerprint(loaded, date, fp2)
    assert normalized.get("params_fingerprint") == fp2
    assert normalized.get("entries") == {}


def test_invalidate_date_cache_rejects_path_traversal(tmp_path: Path):
    """invalidate_date_cache should not delete files outside output_dir even if date is malicious."""

    from src.core.recognition_cache import invalidate_date_cache

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    outside = tmp_path / "outside.json"
    outside.write_text("do not delete", encoding="utf-8")

    # This would resolve to tmp_path/outside.json if not guarded.
    invalidate_date_cache(output_dir, "../../../../outside")
    assert outside.exists()
