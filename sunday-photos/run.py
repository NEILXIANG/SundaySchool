#!/usr/bin/env python3
"""Entry wrapper delegating to src.cli.run.

Important:
- Keep import paths consistent (use src.*) to avoid importing the same code twice
    (e.g. core.* vs src.core.*), which can split global singletons and break tests.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
# Ensure the project root (containing the src/ package) is importable even when
# running from a different working directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.run import main


if __name__ == "__main__":
    main()
