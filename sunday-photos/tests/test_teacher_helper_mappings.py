import json

import pytest


@pytest.mark.parametrize(
    "exc_factory,expected_emoji",
    [
        (lambda: FileNotFoundError("missing"), "📁"),
        (lambda: PermissionError("Permission denied"), "🔒"),
        (lambda: MemoryError("Out of memory"), "🧠"),
        (lambda: ImportError("No module"), "📦"),
        (lambda: UnicodeEncodeError("utf-8", "测", 0, 1, "boom"), "🔤"),
        (lambda: json.JSONDecodeError("Expecting value", "x", 0), "⚙️"),
        (lambda: RuntimeError("network connection failed"), "🌐"),
    ],
)
def test_teacher_helper_maps_common_errors(exc_factory, expected_emoji):
    from ui.teacher_helper import TeacherHelper

    helper = TeacherHelper()
    msg = helper.get_friendly_error(exc_factory(), context="ctx")

    assert expected_emoji in msg
    assert "ctx" in msg


def test_teacher_helper_maps_winerror_206_path_too_long():
    from ui.teacher_helper import TeacherHelper

    class WinPathTooLongError(OSError):
        def __init__(self, message: str):
            super().__init__(message)
            self.winerror = 206

    helper = TeacherHelper()
    msg = helper.get_friendly_error(WinPathTooLongError("WinError 206"), context="ctx")
    assert "📏" in msg


def test_teacher_helper_falls_back_to_general_error():
    from ui.teacher_helper import TeacherHelper

    helper = TeacherHelper()
    msg = helper.get_friendly_error(RuntimeError("something else"), context="ctx")
    assert "⚠️" in msg
    assert "ctx" in msg
