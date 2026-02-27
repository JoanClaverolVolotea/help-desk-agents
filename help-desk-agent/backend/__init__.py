from __future__ import annotations

import pathlib
import sys


def _ensure_repo_src_on_path() -> None:
    """Add the repository `src/` path so local `agents` imports resolve."""
    repo_src = pathlib.Path(__file__).resolve().parents[2] / "src"
    repo_src_str = str(repo_src)
    if not repo_src.is_dir():
        return
    if repo_src_str not in sys.path:
        sys.path.insert(0, repo_src_str)


_ensure_repo_src_on_path()
