"""Top-level compatibility entrypoint.

This project historically supported importing `main` directly:

    from main import SimplePhotoOrganizer

Depending on how PYTHONPATH is configured, the real implementation may live under
`src/` (preferred) or be imported as the `core` package.

This shim makes `import main` work reliably by ensuring `sunday-photos/src` is on
`sys.path` and then re-exporting the canonical symbols.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SRC_DIR = (Path(__file__).resolve().parent / "src").as_posix()
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# After sys.path adjustment, `core.*` should be importable.
from core.main import (  # noqa: E402
    ConfigLoader,
    ServiceContainer,
    SimplePhotoOrganizer,
    UnknownClustering,
    parallel_recognize,
)

__all__ = [
    "SimplePhotoOrganizer",
    "ConfigLoader",
    "ServiceContainer",
    "parallel_recognize",
    "UnknownClustering",
]


def main() -> None:
    """CLI entrypoint."""

    from cli.run import main as cli_main  # noqa: E402

    cli_main()


if __name__ == "__main__":
    main()
