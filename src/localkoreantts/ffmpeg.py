"""Best-effort ffmpeg detection with macOS friendly fallbacks."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
from typing import Iterable, Optional

LK_TTS_FFMPEG_ENV = "LK_TTS_FFMPEG_BIN"

COMMON_MAC_PATHS = (
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/local/bin/ffmpeg",
)


def _candidate_paths() -> Iterable[Path]:
    seen = set()
    which_path = shutil.which("ffmpeg")
    if which_path:
        path = Path(which_path)
        seen.add(path)
        yield path

    env_path = os.environ.get(LK_TTS_FFMPEG_ENV)
    if env_path:
        path = Path(env_path).expanduser()
        if path not in seen:
            seen.add(path)
            yield path

    for candidate in COMMON_MAC_PATHS:
        path = Path(candidate)
        if path in seen:
            continue
        yield path


def detect_ffmpeg_path(explicit: Optional[str] = None) -> Optional[Path]:
    """Return the ffmpeg binary path if available."""

    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return path
        raise FileNotFoundError(f"Provided ffmpeg path '{path}' is not executable")

    for path in _candidate_paths():
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def find_ffmpeg(explicit: Optional[str] = None) -> Path:
    """Return the ffmpeg binary path or raise a helpful error."""

    path = detect_ffmpeg_path(explicit=explicit)
    if path:
        return path
    raise FileNotFoundError(
        "ffmpeg not found. Install via 'brew install ffmpeg', set LK_TTS_FFMPEG_BIN, or supply --ffmpeg-path."
    )


def describe_ffmpeg(path: Path) -> str:
    """Return the version string for diagnostics."""

    try:
        result = subprocess.run(
            [str(path), "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except OSError:
        return "ffmpeg=<unavailable>"

    first_line = result.stdout.splitlines()[0] if result.stdout else "ffmpeg"
    return first_line.strip()
