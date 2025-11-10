"""Runtime configuration helpers for CLI/GUI diagnostics."""

from __future__ import annotations

from pathlib import Path
import os
import platform
from typing import Dict, Optional

from .paths import (
    LK_TTS_CACHE_ENV,
    LK_TTS_MODEL_ENV,
    PathConfig,
    resolve_path_config,
)
from .ffmpeg import (
    LK_TTS_FFMPEG_ENV,
    detect_ffmpeg_path,
)


def _redact_path(path: Path) -> str:
    home = Path.home().expanduser()
    path = Path(path).expanduser()
    try:
        relative = path.relative_to(home)
        return f"~/{relative}"
    except ValueError:
        return str(path)


def _stringify_path(value: Optional[Path], redact: bool) -> Optional[str]:
    if value is None:
        return None
    if redact:
        return _redact_path(value)
    return str(Path(value))


def get_paths(redact: bool = False) -> Dict[str, object]:
    """Return a dictionary describing resolved paths and env overrides."""

    config = resolve_path_config()
    ffmpeg_path = detect_ffmpeg_path()

    info: Dict[str, object] = {
        "platform": platform.system(),
        "platform_detail": platform.platform(),
        "model_dir": _stringify_path(config.model_dir, redact),
        "cache_dir": _stringify_path(config.cache_dir, redact),
        "ffmpeg_bin": _stringify_path(ffmpeg_path, redact),
        "env": {
            LK_TTS_MODEL_ENV: os.environ.get(LK_TTS_MODEL_ENV),
            LK_TTS_CACHE_ENV: os.environ.get(LK_TTS_CACHE_ENV),
            LK_TTS_FFMPEG_ENV: os.environ.get(LK_TTS_FFMPEG_ENV),
        },
    }
    return info


def describe_environment(redact: bool = True) -> str:
    """Human friendly summary used when --describe is invoked."""

    data = get_paths(redact=redact)
    fields = [
        f"platform={data['platform_detail']}",
        f"model_dir={data['model_dir']}",
        f"cache_dir={data['cache_dir']}",
        f"ffmpeg={data['ffmpeg_bin'] or 'unset'}",
    ]
    return ", ".join(fields)
