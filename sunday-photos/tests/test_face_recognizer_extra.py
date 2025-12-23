import numpy as np
import pytest
from unittest.mock import MagicMock
from pathlib import Path

import src.core.face_recognizer as fr_module
from src.core.face_recognizer import FaceRecognizer


def _make_fr(monkeypatch, tmp_path):
    # Prevent expensive/IO in constructor
    monkeypatch.setattr(fr_module.FaceRecognizer, "load_student_encodings", lambda self: None)
    sm = MagicMock()
    sm.input_dir = tmp_path
    return FaceRecognizer(sm)


def test_get_recognition_confidence_with_single_encoding(monkeypatch, tmp_path):
    fr = _make_fr(monkeypatch, tmp_path)

    # Prepare students_encodings with the expected key used in load_student_encodings ("encodings")
    fr.students_encodings = {"Alice": {"name": "Alice", "encodings": [np.zeros(128)]}}

    # Patch face_recognition functions inside the module under test
    monkeypatch.setattr(fr_module.face_recognition, "load_image_file", lambda p: np.zeros((128, 128, 3)))
    monkeypatch.setattr(fr_module.face_recognition, "face_locations", lambda img: [(0, 80, 120, 0)])
    monkeypatch.setattr(fr_module.face_recognition, "face_encodings", lambda img, locs: [np.zeros(128)])
    monkeypatch.setattr(fr_module.face_recognition, "face_distance", lambda known, enc: np.array([0.1]))

    conf = fr.get_recognition_confidence(str(tmp_path / "fake.jpg"), "Alice")
    # Expect confidence = 1 - min_distance = 0.9
    assert pytest.approx(conf, rel=1e-6) == 0.9


def test_verify_student_photo_returns_expected(monkeypatch, tmp_path):
    fr = _make_fr(monkeypatch, tmp_path)

    # Monkeypatch recognize_faces to return a predictable list
    monkeypatch.setattr(fr, "recognize_faces", lambda image_path: ["Bob"])

    assert fr.verify_student_photo("Bob", "x.jpg") is True
    assert fr.verify_student_photo("Alice", "x.jpg") is False


def test_update_student_encoding_updates_state(monkeypatch, tmp_path):
    fr = _make_fr(monkeypatch, tmp_path)

    # Prepare a student entry
    fr.students_encodings = {"Student15": {"name": "Student15", "encodings": [np.zeros(128)]}}

    # Patch face_recognition to return a new encoding for the update
    monkeypatch.setattr(fr_module.face_recognition, "load_image_file", lambda p: np.zeros((128, 128, 3)))
    monkeypatch.setattr(fr_module.face_recognition, "face_locations", lambda img: [(0, 80, 120, 0)])
    monkeypatch.setattr(fr_module.face_recognition, "face_encodings", lambda img, locs: [np.ones(128)])

    # Write a dummy file to satisfy existence check
    new_photo = tmp_path / "new.jpg"
    new_photo.write_bytes(b"fake")

    updated = fr.update_student_encoding("Student15", str(new_photo))
    assert updated is True
    assert "Student15" in fr.known_student_names
    assert len(fr.students_encodings["Student15"]["encodings"]) == 1


def test_update_student_encoding_returns_false_for_missing_file(monkeypatch, tmp_path):
    fr = _make_fr(monkeypatch, tmp_path)

    result = fr.update_student_encoding("NoSuchStudent", str(tmp_path / "no.jpg"))
    assert result is False


def test_update_student_encoding_persists_to_snapshot(monkeypatch, tmp_path):
    """验证update_student_encoding会持久化到snapshot和缓存文件"""
    fr = _make_fr(monkeypatch, tmp_path)

    # 准备学生条目
    fr.students_encodings = {"Student15": {"name": "Student15", "encodings": [np.zeros(128)]}}

    # Patch face_recognition
    monkeypatch.setattr(fr_module.face_recognition, "load_image_file", lambda p: np.zeros((128, 128, 3)))
    monkeypatch.setattr(fr_module.face_recognition, "face_locations", lambda img: [(0, 80, 120, 0)])
    monkeypatch.setattr(fr_module.face_recognition, "face_encodings", lambda img, locs: [np.ones(128)])

    # 写入虚拟文件
    new_photo = tmp_path / "new.jpg"
    new_photo.write_bytes(b"fake")

    # 执行更新
    updated = fr.update_student_encoding("Student15", str(new_photo))
    assert updated is True

    # 验证snapshot已更新
    snapshot = fr._load_ref_snapshot()
    assert snapshot is not None
    assert "students" in snapshot
    assert "Student15" in snapshot["students"]
    assert len(snapshot["students"]["Student15"]) == 1
    assert snapshot["students"]["Student15"][0]["status"] == "ok"
    
    # 验证缓存文件存在
    cache_file = snapshot["students"]["Student15"][0].get("cache")
    assert cache_file is not None
    cache_path = fr._ref_cache_dir / cache_file
    assert cache_path.exists()
