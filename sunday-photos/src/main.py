"""兼容入口（薄封装）。

说明：
- 该文件历史上包含一套独立实现，长期存在与 `core.main` 漂移的风险。
- 现在收敛为“兼容 shim”：保留 `import main`/`from main import SimplePhotoOrganizer` 的导入路径，
  但权威实现以 `core.main` 为准。
"""

from __future__ import annotations

from core.main import ConfigLoader, SimplePhotoOrganizer, parallel_recognize

__all__ = ["SimplePhotoOrganizer", "ConfigLoader", "parallel_recognize"]


def main() -> None:
    """命令行运行入口：转交给 `cli.run`。"""

    from cli.run import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()