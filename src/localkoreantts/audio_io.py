"""Audio playback helpers that isolate the sounddevice dependency."""

from __future__ import annotations

from pathlib import Path
import os
from typing import Optional, Tuple

import numpy as np

LK_TTS_SAMPLE_RATE_ENV = "LK_TTS_SAMPLE_RATE"

try:
    import soundfile as sf
except Exception:  # pragma: no cover - optional dependency path
    sf = None

try:
    from scipy.io import wavfile as scipy_wavfile
except Exception:  # pragma: no cover - optional dependency path
    scipy_wavfile = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - dependency missing
    sd = None


class AudioPlaybackError(RuntimeError):
    """Raised when playback cannot proceed."""


def _load_wave(path: Path) -> Tuple[np.ndarray, int]:
    if sf is not None:
        data, rate = sf.read(str(path), always_2d=False)
        return _coerce_to_float32(data), rate
    if scipy_wavfile is not None:
        rate, data = scipy_wavfile.read(str(path))
        return _coerce_to_float32(data), rate
    raise AudioPlaybackError(
        "Cannot read audio without 'soundfile' or 'scipy'. Install soundfile via pip."
    )


def _coerce_to_float32(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data)
    if arr.dtype == np.float32:
        return arr
    if np.issubdtype(arr.dtype, np.integer):
        info = np.iinfo(arr.dtype)
        max_abs = max(abs(info.min), info.max)
        if max_abs == 0:
            return arr.astype(np.float32)
        return (arr.astype(np.float32) / max_abs).astype(np.float32)
    return arr.astype(np.float32)


def _resolve_sample_rate(explicit: Optional[int], fallback: Optional[int]) -> int:
    if explicit:
        return explicit
    env_value = os.environ.get(LK_TTS_SAMPLE_RATE_ENV)
    if env_value:
        try:
            return int(env_value)
        except ValueError as exc:
            raise AudioPlaybackError(
                f"Invalid LK_TTS_SAMPLE_RATE value '{env_value}'. Provide an integer."
            ) from exc
    if fallback:
        return fallback
    raise AudioPlaybackError(
        "Sample rate could not be determined. Supply samplerate or set LK_TTS_SAMPLE_RATE."
    )


def play_wav(
    path: Path | str,
    *,
    device: Optional[str | int] = None,
    samplerate: Optional[int] = None,
    skip_play: bool = False,
) -> None:
    """Play a WAV file via sounddevice, converting to numpy arrays."""

    target = Path(path)
    if skip_play:
        return

    if not target.is_file():
        raise AudioPlaybackError(f"Audio file '{target}' does not exist.")

    if sd is None:
        raise AudioPlaybackError(
            "sounddevice is unavailable. Re-run with skip_play=True to bypass playback."
        )

    audio, detected_rate = _load_wave(target)
    rate = _resolve_sample_rate(samplerate, detected_rate)

    try:
        sd.play(audio, samplerate=rate, device=device)
        sd.wait()
    except Exception as exc:  # pragma: no cover - depends on host audio stack
        raise AudioPlaybackError(
            "Audio playback failed (device unavailable?). "
            "Re-run with skip_play=True to generate files only."
        ) from exc
