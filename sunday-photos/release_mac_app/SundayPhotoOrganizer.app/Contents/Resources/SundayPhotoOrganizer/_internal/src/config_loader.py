"""兼容层（shim）：保持历史导入路径不变。

历史上部分脚本会从 `config_loader` 导入 `ConfigLoader`。
当前权威实现位于 `core.config_loader`。
"""

from core.config_loader import ConfigLoader  # noqa: F401