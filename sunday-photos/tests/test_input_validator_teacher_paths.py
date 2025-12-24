from pathlib import Path

from src.ui.input_validator import InputValidator
from tests.testdata_builder import write_empty_file, write_jpeg


def test_validate_student_photos_allows_empty_root_as_warning(tmp_path: Path):
    base = tmp_path / "input" / "student_photos"
    base.mkdir(parents=True, exist_ok=True)

    # 夹带平台垃圾文件：不应被当作学生文件夹
    (base / ".DS_Store").write_text("x", encoding="utf-8")
    (base / "__MACOSX").mkdir(parents=True, exist_ok=True)
    (base / "._IMG_0001.jpg").write_text("x", encoding="utf-8")

    v = InputValidator()
    result = v.validate_student_photos_directory(str(base))

    assert result["valid"] is True
    assert result["student_count"] == 0
    assert "unknown" in result["message"]


def test_validate_student_photos_rejects_root_images(tmp_path: Path):
    base = tmp_path / "input" / "student_photos"
    write_jpeg(base / "SHOULD_NOT_BE_HERE.jpg", text="illegal", seed=1)

    v = InputValidator()
    result = v.validate_student_photos_directory(str(base))

    assert result["valid"] is False
    msg = result["message"]
    assert "唯一正确方式" in msg
    assert "student_photos 根目录发现图片" in msg


def test_validate_student_photos_rejects_nested_student_dirs(tmp_path: Path):
    base = tmp_path / "input" / "student_photos"
    nested = base / "Alice" / "more"
    nested.mkdir(parents=True, exist_ok=True)
    write_jpeg(base / "Bob" / "ref.jpg", text="ok", seed=2)

    v = InputValidator()
    result = v.validate_student_photos_directory(str(base))

    assert result["valid"] is False
    assert "不支持嵌套" in result["message"]


def test_validate_student_photos_rejects_empty_student_folder(tmp_path: Path):
    base = tmp_path / "input" / "student_photos"
    (base / "Alice").mkdir(parents=True, exist_ok=True)
    write_jpeg(base / "Bob" / "ref.jpg", text="ok", seed=3)

    v = InputValidator()
    result = v.validate_student_photos_directory(str(base))

    assert result["valid"] is False
    assert "为空或没有图片" in result["message"]


def test_validate_photo_file_rejects_unsupported_extension(tmp_path: Path):
    p = tmp_path / "x.gif"
    p.write_bytes(b"not-empty")

    v = InputValidator()
    result = v.validate_photo_file(str(p))

    assert result["valid"] is False
    assert "照片格式不支持" in result["message"]


def test_validate_photo_file_rejects_zero_byte_supported_image(tmp_path: Path):
    p = tmp_path / "x.jpg"
    write_empty_file(p)

    v = InputValidator()
    result = v.validate_photo_file(str(p))

    assert result["valid"] is False
    assert "照片文件为空" in result["message"]
