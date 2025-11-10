"""Helpers for verifying that model assets exist before synthesis."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .paths import PathConfig


class ModelNotReadyError(RuntimeError):
    """Raised when the expected model assets are missing."""


def _has_files(root: Path) -> bool:
    return any(child.is_file() for child in root.rglob("*"))


def ensure_model_ready(config: PathConfig) -> None:
    model_dir = config.model_dir
    if not model_dir.exists():
        raise ModelNotReadyError(
            f"Model directory '{model_dir}' is missing. "
            "Run 'python scripts/setup_test_model.py' to download a sample bundle."
        )
    if not _has_files(model_dir):
        raise ModelNotReadyError(
            f"Model directory '{model_dir}' is empty. "
            "Populate it with weights or run 'python scripts/setup_test_model.py'."
        )
