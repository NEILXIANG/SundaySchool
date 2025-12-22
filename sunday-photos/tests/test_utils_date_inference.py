#!/usr/bin/env python3
"""工具函数日期推断规则测试。

覆盖点：
- `get_photo_date()` 必须优先使用目录名 YYYY-MM-DD（即使图片内容为空/无法解析）。

为什么要测：
- 教师最常见的组织方式是按日期建文件夹；目录名往往比 EXIF 更可靠。
- 如果目录名可用，则不应该再去读 EXIF（减少对损坏图片/空文件的异常噪音）。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def test_get_photo_date_prefers_directory_name() -> None:
    from core.utils import get_photo_date

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        photo = base / "class_photos" / "2025-12-21" / "a.jpg"
        photo.parent.mkdir(parents=True, exist_ok=True)

        # 写入一个“非空但非真实 JPEG”的文件：
        # 只要目录名可用，get_photo_date() 应直接返回目录日期，不去读 EXIF。
        photo.write_bytes(b"not-a-real-jpeg")

        with mock.patch("PIL.Image.open", side_effect=AssertionError("不应尝试读取 EXIF")):
            assert get_photo_date(str(photo)) == "2025-12-21"


def main() -> None:
    test_get_photo_date_prefers_directory_name()
    print("✓ 日期推断规则测试通过")


if __name__ == "__main__":
    main()
