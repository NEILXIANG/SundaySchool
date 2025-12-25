import os
import time
from pathlib import Path

from src.core.utils import is_ignored_fs_entry, get_photo_date
from tests.testdata_builder import write_jpeg


def test_is_ignored_fs_entry_common_cases():
    assert is_ignored_fs_entry(Path(".DS_Store"))
    assert is_ignored_fs_entry(Path("__MACOSX"))
    assert is_ignored_fs_entry(Path("._IMG_0001.jpg"))
    assert is_ignored_fs_entry(Path("desktop.ini"))
    assert is_ignored_fs_entry(Path("Thumbs.db"))

    # 正常文件不应被忽略
    assert not is_ignored_fs_entry(Path("IMG_0001.jpg"))


def test_get_photo_date_prefers_date_directory(tmp_path: Path):
    # 构造：class_photos/2025-12-21/img.jpg，但文件 mtime 设为另一日期
    date_dir = tmp_path / "class_photos" / "2025-12-21"
    img = date_dir / "img.jpg"
    write_jpeg(img, text="x", seed=1)

    # 设一个不同的 mtime（不应影响结果）
    other = int(time.time()) - 86400 * 30
    os.utime(img, (other, other))

    assert get_photo_date(str(img)) == "2025-12-21"


def test_get_photo_date_closes_image_handle(monkeypatch, tmp_path: Path):
    # 构造一个不含日期目录的路径，迫使进入 EXIF/mtime 分支
    img = tmp_path / "img.jpg"
    img.write_bytes(b"not-a-real-jpeg-but-nonempty")

    # 设定一个固定 mtime，便于断言返回格式有效
    fixed = 1766275200  # 2025-12-21 00:00:00 UTC-ish; 仅用于稳定测试
    os.utime(img, (fixed, fixed))

    opened = {"obj": None}

    class DummyImage:
        def __init__(self):
            self.closed = False

        def _getexif(self):
            return None

        def close(self):
            self.closed = True

    def fake_open(_path):
        opened["obj"] = DummyImage()
        return opened["obj"]

    import PIL.Image

    monkeypatch.setattr(PIL.Image, "open", fake_open)

    result = get_photo_date(str(img))
    assert isinstance(result, str) and len(result) == 10
    assert opened["obj"] is not None
    assert opened["obj"].closed is True
