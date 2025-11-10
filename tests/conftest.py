import os
import sys

import pytest


@pytest.fixture(autouse=True)
def _mock_sounddevice(monkeypatch):
    """Replace sounddevice playback with a benign stub for every test."""

    from localkoreantts import audio_io

    class DummySD:
        def __init__(self):
            self.play_calls = []

        def play(self, data, samplerate=None, device=None):
            self.play_calls.append(
                {"samples": len(data), "samplerate": samplerate, "device": device}
            )

        def wait(self):
            return None

    monkeypatch.setattr(audio_io, "sd", DummySD())


@pytest.fixture(autouse=True)
def _mock_ffmpeg_bin(monkeypatch, tmp_path_factory):
    """Provide a dummy ffmpeg binary path so detection never hits the host system."""

    ffmpeg_dir = tmp_path_factory.mktemp("ffmpeg-bin")
    fake_ffmpeg = ffmpeg_dir / "ffmpeg"
    fake_ffmpeg.write_text("#!/bin/sh\nexit 0\n")
    fake_ffmpeg.chmod(0o755)
    monkeypatch.setenv("LK_TTS_FFMPEG_BIN", str(fake_ffmpeg))


@pytest.fixture(autouse=True)
def _force_offscreen_qt(monkeypatch):
    """Force PySide6 to use the offscreen platform plugin on macOS."""

    if sys.platform == "darwin":
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
