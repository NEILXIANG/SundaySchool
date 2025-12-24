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
