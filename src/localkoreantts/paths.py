"""Utilities for resolving model/cache paths in a cross-platform way."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
from typing import Tuple

LK_TTS_MODEL_ENV = "LK_TTS_MODEL_PATH"
LK_TTS_CACHE_ENV = "LK_TTS_CACHE_DIR"

_SYSTEM = platform.system()


def _expand_env_path(value: str | Path) -> Path:
    return Path(value).expanduser()


def _xdg_dir(env_name: str, fallback: Path) -> Path:
    custom = os.environ.get(env_name)
    if custom:
        return _expand_env_path(custom)
    return fallback


def _windows_local_appdata() -> Path:
    return _expand_env_path(
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("APPDATA")
        or (Path.home() / "AppData" / "Local")
    )


def _default_model_dir() -> Path:
    if _SYSTEM == "Windows":
        base = _windows_local_appdata()
        return base / "LocalKoreanTTS" / "model"
    base = _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")
    return base / "localkoreantts" / "model"


def _default_cache_dir() -> Path:
    if _SYSTEM == "Windows":
        base = _windows_local_appdata()
        return base / "LocalKoreanTTS" / "cache"
    base = _xdg_dir("XDG_CACHE_HOME", Path.home() / ".cache")
    return base / "localkoreantts"


@dataclass(frozen=True)
class PathConfig:
    """Normalized locations for model + cache directories."""

    model_dir: Path
    cache_dir: Path

    def ensure(self) -> "PathConfig":
        """Create directories if needed and return the same config."""
        for directory in (self.model_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def as_tuple(self) -> Tuple[Path, Path]:
        return self.model_dir, self.cache_dir


def resolve_path_config() -> PathConfig:
    """Resolve the directories, honoring environment overrides."""

    model_dir = Path(
        os.environ.get(LK_TTS_MODEL_ENV, _default_model_dir())
    ).expanduser()
    cache_dir = Path(
        os.environ.get(LK_TTS_CACHE_ENV, _default_cache_dir())
    ).expanduser()

    config = PathConfig(model_dir=model_dir, cache_dir=cache_dir).ensure()
    return config


def describe_environment() -> str:
    """Human readable description used in logs and diagnostics."""

    config = resolve_path_config()
    parts = [
        f"platform={platform.platform()}",
        f"model_dir={config.model_dir}",
        f"cache_dir={config.cache_dir}",
    ]
    return ", ".join(parts)
