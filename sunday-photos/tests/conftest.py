import sys
import types
from pathlib import Path


def _install_face_recognition_stub() -> None:
    """在测试环境中提供 face_recognition 的最小 stub。

    目的：
    - 让 `unittest.mock.patch("face_recognition....")` 在依赖缺失时仍可工作。
    - 若用户已安装真实 face_recognition，则不会触发此逻辑。
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


try:
    import face_recognition  # type: ignore  # noqa: F401
except Exception:
    _install_face_recognition_stub()


def create_minimal_test_image(path: Path) -> None:
    """创建一个最小的测试图片文件（非空，可通过 is_supported_nonempty_image_path 检查）。
    
    说明：测试不应依赖可解码的真实图片（避免引入 PIL/face_recognition 解析开销），
    只需确保文件非空即可通过扫描与加载阶段的校验。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # 使用任意非空字节（例如 "fake image"）
    path.write_bytes(b"fake-test-image-data")
