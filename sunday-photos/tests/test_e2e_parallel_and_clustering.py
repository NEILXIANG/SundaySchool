import json
from pathlib import Path

import pytest

import src.core.main as core_main
from src.core.config import REPORT_FILE, UNKNOWN_PHOTOS_DIR
from src.core.file_organizer import FileOrganizer
from src.core.main import SimplePhotoOrganizer
from src.core.student_manager import StudentManager


class FakeFRForSerialFallback:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "serial-fp"
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []
        self.calls = []

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        self.calls.append(photo_path)
        p = Path(photo_path)
        # 简单规则：img_01 -> Bob，img_02 -> unknown
        if p.name == "img_01.jpg":
            return {"status": "success", "recognized_students": ["Bob"], "unknown_encodings": []}
        return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}


class FakeFRForUnknownClustering:
    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "cluster-fp"
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        # 让两张 unknown 都带 unknown_encodings，从而触发聚类分支
        return {
            "status": "no_matches_found",
            "recognized_students": [],
            "unknown_encodings": [[0.1, 0.2, 0.3]],
        }


class FakeFRForParallelSuccess:
    """用于验证并行成功路径：如果触发串行回退，此类会让测试失败。"""

    def __init__(self, student_manager: StudentManager):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = "parallel-success-fp"
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, *_args, **_kwargs):
        raise AssertionError("recognize_faces() should not be called when parallel_recognize succeeds")


class SC:
    def __init__(self, input_dir: Path, output_dir: Path, face_recognizer):
        self._student_manager = StudentManager(input_dir=str(input_dir))
        self._face_recognizer = face_recognizer(self._student_manager)
        self._file_organizer = FileOrganizer(output_dir=str(output_dir))

    def get_student_manager(self):
        return self._student_manager

    def get_face_recognizer(self):
        return self._face_recognizer

    def get_file_organizer(self):
        return self._file_organizer


def _write_config(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_e2e_parallel_recognition_fallback_to_serial(offline_generated_dataset, monkeypatch):
    ds = offline_generated_dataset

    # 开启并行，且阈值很低，确保走并行分支
    cfg_path = ds.input_dir.parent / "config.json"
    _write_config(
        cfg_path,
        {
            "parallel_recognition": {"enabled": True, "workers": 2, "chunk_size": 1, "min_photos": 1},
            "unknown_face_clustering": {"enabled": False},
        },
    )

    # 让 parallel_recognize 抛异常，验证会回退到 face_recognizer.recognize_faces
    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(core_main, "parallel_recognize", _boom)

    sc = SC(ds.input_dir, ds.output_dir, FakeFRForSerialFallback)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=sc,
        config_file=str(cfg_path),
    )

    assert organizer.run() is True

    # 回退应确实调用了串行识别
    assert len(sc.get_face_recognizer().calls) >= 1

    # 至少有输出与报告
    reports = list(ds.output_dir.glob(f"*_{REPORT_FILE}"))
    assert len(reports) == 1


def test_e2e_unknown_clustering_enabled_places_cluster_folders(offline_generated_dataset, monkeypatch):
    ds = offline_generated_dataset

    cfg_path = ds.input_dir.parent / "config.json"
    _write_config(
        cfg_path,
        {
            "parallel_recognition": {"enabled": False, "workers": 1, "chunk_size": 1, "min_photos": 9999},
            "unknown_face_clustering": {"enabled": True, "threshold": 0.33, "min_cluster_size": 2},
        },
    )

    captured = {"tolerance": None, "min_cluster_size": None, "added": 0}

    class FakeClustering:
        def __init__(self, tolerance: float = 0.45, min_cluster_size: int = 2):
            captured["tolerance"] = tolerance
            captured["min_cluster_size"] = min_cluster_size
            self._paths = []

        def add_faces(self, path: str, encodings):
            self._paths.append(path)

        def get_results(self):
            # 将所有 unknown 聚到一个簇
            return {"Unknown_Person_1": list(self._paths)}

    monkeypatch.setattr(core_main, "UnknownClustering", FakeClustering)

    sc = SC(ds.input_dir, ds.output_dir, FakeFRForUnknownClustering)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=sc,
        config_file=str(cfg_path),
    )

    assert organizer.run() is True

    # 参数透传
    assert captured["tolerance"] == pytest.approx(0.33)
    assert captured["min_cluster_size"] == 2

    # 应产生 unknown_photos/Unknown_Person_1/<date>/...
    cluster_dir = ds.output_dir / UNKNOWN_PHOTOS_DIR / "Unknown_Person_1"
    assert cluster_dir.exists()
    # 至少有一个日期子目录
    assert any(p.is_dir() for p in cluster_dir.iterdir())


def test_e2e_parallel_recognize_success_path(offline_generated_dataset, monkeypatch):
    ds = offline_generated_dataset

    # 开启并行，阈值很低，确保走并行分支
    cfg_path = ds.input_dir.parent / "config.json"
    _write_config(
        cfg_path,
        {
            "parallel_recognition": {"enabled": True, "workers": 2, "chunk_size": 1, "min_photos": 1},
            "unknown_face_clustering": {"enabled": False},
        },
    )

    calls = {"parallel": 0}

    def _fake_parallel_recognize(photo_paths, **_kwargs):
        calls["parallel"] += 1
        for p in photo_paths:
            pp = Path(p)
            key = pp.as_posix()
            if "/2025-12-21/" in key and pp.name == "img_01.jpg":
                yield p, {"status": "success", "recognized_students": ["Alice"], "unknown_encodings": []}
            elif "/2025-12-22/" in key and pp.name == "img_01.jpg":
                yield p, {"status": "success", "recognized_students": ["Bob"], "unknown_encodings": []}
            else:
                yield p, {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}

    monkeypatch.setattr(core_main, "parallel_recognize", _fake_parallel_recognize)

    sc = SC(ds.input_dir, ds.output_dir, FakeFRForParallelSuccess)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=sc,
        config_file=str(cfg_path),
    )

    assert organizer.run() is True
    assert calls["parallel"] >= 1

    # 并行识别结果应正确落盘
    assert (ds.output_dir / "Alice" / "2025-12-21" / "img_01.jpg").exists()
    assert (ds.output_dir / "Bob" / "2025-12-22" / "img_01.jpg").exists()
    # unknown 应进 unknown_photos
    assert (ds.output_dir / UNKNOWN_PHOTOS_DIR / "2025-12-21" / "img_02.jpg").exists()
