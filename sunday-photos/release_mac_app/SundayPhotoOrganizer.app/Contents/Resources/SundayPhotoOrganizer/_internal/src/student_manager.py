"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `student_manager` 导入 `StudentManager`。
当前权威实现位于 `core.student_manager`。
"""

from core.student_manager import StudentManager  # noqa: F401