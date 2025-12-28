"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `file_organizer` 导入 `FileOrganizer`。
当前权威实现位于 `core.file_organizer`。
"""

from core.file_organizer import FileOrganizer  # noqa: F401