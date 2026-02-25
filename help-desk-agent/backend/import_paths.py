from __future__ import annotations

import pathlib
import sys


def configure_backend_import_paths(current_file: str) -> None:
    current_dir = pathlib.Path(current_file).resolve().parent
    repo_root = current_dir.parent.parent
    src_dir = repo_root / "src"

    _prepend_if_missing(src_dir, index=0)
    _prepend_if_missing(repo_root, index=1)
    _prepend_if_missing(current_dir, index=2)


def _prepend_if_missing(path: pathlib.Path, index: int) -> None:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(index, path_str)
