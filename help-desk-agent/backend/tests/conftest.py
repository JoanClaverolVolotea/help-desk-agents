from __future__ import annotations

import pathlib
import sys

HELP_DESK_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(HELP_DESK_DIR) not in sys.path:
    sys.path.insert(0, str(HELP_DESK_DIR))
