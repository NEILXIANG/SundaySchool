import sys
import types
import os
import time
from pathlib import Path

import pytest


def _install_face_recognition_stub() -> None:
    """在测试环境中提供 face_recognition 的最小 stub。

    目的：
    - 让测试环境不再意外导入真实 face_recognition（它会引入 dlib 等重依赖，并产生噪声警告）。
    - 兼容历史：若未来仍有测试想 patch `face_recognition.*`，也能顺利 patch 到 stub 上。
    """

    if "face_recognition" in sys.modules:
        return

    stub = types.ModuleType("face_recognition")

    def _raise(*_args, **_kwargs):
        raise ModuleNotFoundError(
            "未安装 face_recognition（人脸识别依赖）。这是测试用 stub；请在真实运行环境安装 requirements.txt。"
        )

    # 提供测试中会 patch 的常用 API
    stub.load_image_file = _raise
    stub.face_locations = _raise
    stub.face_encodings = _raise
    stub.compare_faces = _raise
    stub.face_distance = _raise

    sys.modules["face_recognition"] = stub


# 迁移到 InsightFace 后，项目不再依赖 face_recognition；测试中统一注入 stub，避免导入真实包。
_install_face_recognition_stub()


def create_minimal_test_image(path: Path) -> None:
    """创建一个最小的测试图片文件（非空，可通过 is_supported_nonempty_image_path 检查）。
    
    说明：测试不应依赖可解码的真实图片（避免引入 PIL/face_recognition 解析开销），
    只需确保文件非空即可通过扫描与加载阶段的校验。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # 使用任意非空字节（例如 "fake image"）
    path.write_bytes(b"fake-test-image-data")


def _set_mtime(path: Path, mtime_sec: int) -> None:
    os.utime(path, (mtime_sec, mtime_sec))


@pytest.fixture()
def offline_generated_dataset(tmp_path: Path):
    """构建一份完全离线、可重复的测试数据集。

    结构：
    - input/student_photos/<学生名>/*.jpg
    - input/class_photos/<YYYY-MM-DD>/*.jpg
    - output/, logs/ 作为运行输出目录
    """
    from tests.testdata_builder import GeneratedDataset, write_jpeg, write_empty_file

    input_dir = tmp_path / "input"
    student_dir = input_dir / "student_photos"
    class_dir = input_dir / "class_photos"
    output_dir = tmp_path / "output"
    log_dir = tmp_path / "logs"

    student_names = ["Alice", "Bob"]
    dates = ["2025-12-21", "2025-12-22"]

    # 学生参考照：Alice 放 6 张（用于验证“最多取 5 张、按 mtime 最新优先”）
    # mtime 使用递增秒，保证跨平台稳定。
    base_mtime = int(time.time()) - 10_000
    alice_dir = student_dir / "Alice"
    for i in range(6):
        p = alice_dir / f"ref_{i+1:02d}.jpg"
        write_jpeg(p, text=f"Alice ref {i+1}", seed=i)
        _set_mtime(p, base_mtime + i)

    # Bob 放 2 张
    bob_dir = student_dir / "Bob"
    for i in range(2):
        p = bob_dir / f"ref_{i+1:02d}.jpg"
        write_jpeg(p, text=f"Bob ref {i+1}", seed=100 + i)
        _set_mtime(p, base_mtime + 100 + i)

    # 课堂照片：每个日期 2 张真实 JPEG + 1 个 0 字节坏文件（应被忽略）
    for date in dates:
        d = class_dir / date
        write_jpeg(d / "img_01.jpg", text=f"class {date} 1", seed=200)
        write_jpeg(d / "img_02.jpg", text=f"class {date} 2", seed=201)
        write_empty_file(d / "bad_00.jpg")

    # 平台垃圾文件（应被忽略）
    (class_dir / ".DS_Store").write_text("x", encoding="utf-8")
    (class_dir / "__MACOSX").mkdir(parents=True, exist_ok=True)
    (class_dir / "__MACOSX" / "junk").write_text("x", encoding="utf-8")
    (class_dir / "._IMG_0001.jpg").write_text("x", encoding="utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    return GeneratedDataset(
        input_dir=input_dir,
        student_dir=student_dir,
        class_dir=class_dir,
        output_dir=output_dir,
        log_dir=log_dir,
        student_names=student_names,
        dates=dates,
    )


@pytest.fixture()
def student_photos_root_image_input(tmp_path: Path) -> Path:
    """构造一个“student_photos 根目录直接放图片”的非法输入，用于校验报错。"""
    from tests.testdata_builder import write_jpeg

    input_dir = tmp_path / "input"
    root = input_dir / "student_photos"
    write_jpeg(root / "SHOULD_NOT_BE_HERE.jpg", text="illegal", seed=999)
    return input_dir
