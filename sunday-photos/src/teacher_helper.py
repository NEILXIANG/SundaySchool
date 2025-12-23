"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `teacher_helper` 导入教师友好提示相关工具。
当前权威实现位于 `ui.teacher_helper`。
"""

from ui.teacher_helper import *  # noqa: F401,F403
