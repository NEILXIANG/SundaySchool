import json
from pathlib import Path

from src.core.config import REPORT_FILE, UNKNOWN_PHOTOS_DIR
from src.core.file_organizer import FileOrganizer
from src.core.main import SimplePhotoOrganizer
from src.core.recognition_cache import date_cache_path
from src.core.student_manager import StudentManager
from tests.testdata_builder import write_jpeg


class FakeFaceRecognizer:
    """离线 e2e 测试用的人脸识别替身。

    目标：
    - 不依赖真实人脸识别库推理
    - 返回可预测的识别结果，覆盖 success / no_matches_found / no_faces_detected
    """

    def __init__(self, student_manager: StudentManager, *, reference_fingerprint: str = "test-fingerprint"):
        self.student_manager = student_manager
        self.tolerance = 0.6
        self.min_face_size = 50
        self.reference_fingerprint = reference_fingerprint
        self.known_student_names = student_manager.get_student_names()
        self.known_encodings = []

    def recognize_faces(self, photo_path: str, return_details: bool = True):
        p = Path(photo_path)
        # 用路径规则制造稳定分类：
        # - 2025-12-21/img_01.jpg -> Alice
        # - 2025-12-21/img_02.jpg -> unknown
        # - 2025-12-22/img_01.jpg -> Bob
        # - 2025-12-22/img_02.jpg -> no_faces_detected
        key = p.as_posix()

        if "/2025-12-21/" in key and p.name == "img_01.jpg":
            return {"status": "success", "recognized_students": ["Alice"], "unknown_encodings": []}
        if "/2025-12-21/" in key and p.name == "img_02.jpg":
            return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}
        if "/2025-12-22/" in key and p.name == "img_01.jpg":
            return {"status": "success", "recognized_students": ["Bob"], "unknown_encodings": []}
        if "/2025-12-22/" in key and p.name == "img_02.jpg":
            return {"status": "no_faces_detected", "recognized_students": [], "unknown_encodings": []}

        return {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []}


class FakeServiceContainer:
    def __init__(self, input_dir: Path, output_dir: Path, *, reference_fingerprint: str = "test-fingerprint"):
        self._student_manager = StudentManager(input_dir=str(input_dir))
        self._face_recognizer = FakeFaceRecognizer(self._student_manager, reference_fingerprint=reference_fingerprint)
        self._file_organizer = FileOrganizer(output_dir=str(output_dir))

    def get_student_manager(self):
        return self._student_manager

    def get_face_recognizer(self):
        return self._face_recognizer

    def get_file_organizer(self):
        return self._file_organizer


def _write_min_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "parallel_recognition": {"enabled": False, "workers": 1, "chunk_size": 1, "min_photos": 9999},
                "unknown_face_clustering": {"enabled": False},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_e2e_offline_run_creates_expected_outputs(offline_generated_dataset):
    ds = offline_generated_dataset

    config_path = ds.input_dir.parent / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir),
        config_file=str(config_path),
    )

    assert organizer.run() is True

    # 已识别：Alice / Bob
    assert (ds.output_dir / "Alice" / "2025-12-21").exists()
    assert (ds.output_dir / "Alice" / "2025-12-21" / "img_01.jpg").exists()
    assert (ds.output_dir / "Bob" / "2025-12-22").exists()
    assert (ds.output_dir / "Bob" / "2025-12-22" / "img_01.jpg").exists()

    # 未匹配或无人脸：进入 unknown_photos/<date>/
    assert (ds.output_dir / UNKNOWN_PHOTOS_DIR / "2025-12-21" / "img_02.jpg").exists()
    assert (ds.output_dir / UNKNOWN_PHOTOS_DIR / "2025-12-22" / "img_02.jpg").exists()

    # 整理报告生成
    reports = list(ds.output_dir.glob(f"*_{REPORT_FILE}"))
    assert len(reports) == 1
    content = reports[0].read_text(encoding="utf-8")
    assert "主日学课堂照片整理报告" in content
    assert "总复制任务数" in content

    # 增量快照生成
    snapshot = ds.output_dir / ".state" / "class_photos_snapshot.json"
    assert snapshot.exists()


def test_e2e_second_run_no_changes_does_not_create_new_report(offline_generated_dataset):
    ds = offline_generated_dataset

    config_path = ds.input_dir.parent / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir),
        config_file=str(config_path),
    )

    assert organizer.run() is True
    reports_after_first = list(ds.output_dir.glob(f"*_{REPORT_FILE}"))
    assert len(reports_after_first) == 1

    # 第二次运行：无新增/变更，应快速结束且不生成新的报告
    assert organizer.run() is True
    reports_after_second = list(ds.output_dir.glob(f"*_{REPORT_FILE}"))
    assert len(reports_after_second) == 1


def test_e2e_deleted_date_sync_cleans_output_and_cache(offline_generated_dataset):
    ds = offline_generated_dataset

    config_path = ds.input_dir.parent / "config.json"
    _write_min_config(config_path)

    organizer = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir),
        config_file=str(config_path),
    )

    # 首次运行，生成输出
    assert organizer.run() is True

    # 手工创建一个日期缓存文件，模拟已存在缓存
    deleted_date = "2025-12-21"
    cache_file = date_cache_path(ds.output_dir, deleted_date)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps({"version": 1, "date": deleted_date, "params_fingerprint": "x", "entries": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert cache_file.exists()

    # 预期待删除日期在输出中确实存在
    assert (ds.output_dir / "Alice" / deleted_date).exists()
    assert (ds.output_dir / UNKNOWN_PHOTOS_DIR / deleted_date).exists()

    # 删除输入端日期目录
    date_dir = ds.class_dir / deleted_date
    assert date_dir.exists()
    for p in sorted(date_dir.rglob("*"), reverse=True):
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            p.rmdir()
    date_dir.rmdir()

    # 再次运行：应执行删除同步（清理输出 + 删除该日期缓存）
    assert organizer.run() is True

    # 输出清理
    assert not (ds.output_dir / "Alice" / deleted_date).exists()
    assert not (ds.output_dir / UNKNOWN_PHOTOS_DIR / deleted_date).exists()

    # 缓存删除
    assert not cache_file.exists()


def test_e2e_changed_date_rebuild_cleans_old_outputs_and_ignores_old_cache(offline_generated_dataset):
    ds = offline_generated_dataset

    config_path = ds.input_dir.parent / "config.json"
    _write_min_config(config_path)

    # 首次运行：生成输出
    organizer1 = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir, reference_fingerprint="fp-v1"),
        config_file=str(config_path),
    )
    assert organizer1.run() is True

    # 在输出中制造一个“历史残留文件”，应在重建前被清理掉
    residue = ds.output_dir / "Bob" / "2025-12-22" / "old_marker.txt"
    residue.parent.mkdir(parents=True, exist_ok=True)
    residue.write_text("old", encoding="utf-8")
    assert residue.exists()

    # 修改输入端某日期照片，触发 changed_dates
    changed_date = "2025-12-22"
    img = ds.class_dir / changed_date / "img_01.jpg"
    assert img.exists()
    write_jpeg(img, text="changed", seed=999)

    # 写入一个“会导致错误分类”的旧缓存：如果被命中，Bob/img_01 会被当成 unknown
    cache_path = date_cache_path(ds.output_dir, changed_date)
    st = img.stat()
    bad_cache = {
        "version": 1,
        "date": changed_date,
        "params_fingerprint": "will-be-mismatched",
        "entries": {
            f"{changed_date}/img_01.jpg": {
                "size": int(st.st_size),
                "mtime": int(st.st_mtime),
                "result": {"status": "no_matches_found", "recognized_students": [], "unknown_encodings": []},
            }
        },
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(bad_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    assert cache_path.exists()

    # 第二次运行：fingerprint 不同，应忽略上面的缓存并重建输出
    organizer2 = SimplePhotoOrganizer(
        input_dir=str(ds.input_dir),
        output_dir=str(ds.output_dir),
        log_dir=str(ds.log_dir),
        service_container=FakeServiceContainer(ds.input_dir, ds.output_dir, reference_fingerprint="fp-v2"),
        config_file=str(config_path),
    )
    assert organizer2.run() is True

    # 重建应清理历史残留
    assert not residue.exists()

    # 缓存未被误用：Bob 的照片仍应落在 Bob/2025-12-22，而不是 unknown
    assert (ds.output_dir / "Bob" / changed_date / "img_01.jpg").exists()
