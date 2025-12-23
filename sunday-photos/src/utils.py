"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `utils` 导入工具函数。
当前权威实现位于 `core.utils`。
"""

from core.utils import *  # noqa: F401,F403
