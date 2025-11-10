from pathlib import Path

from localkoreantts.config import describe_environment, get_paths
from localkoreantts.ffmpeg import LK_TTS_FFMPEG_ENV
from localkoreantts.paths import LK_TTS_CACHE_ENV, LK_TTS_MODEL_ENV


def test_get_paths_redaction(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))

    model_dir = home / ".local" / "share" / "localkoreantts" / "model"
    cache_dir = home / ".cache" / "localkoreantts"
    ffmpeg_bin = home / "bin" / "ffmpeg"
    ffmpeg_bin.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin.write_text("#!/bin/sh\n")
    ffmpeg_bin.chmod(0o755)

    monkeypatch.setenv(LK_TTS_MODEL_ENV, str(model_dir))
    monkeypatch.setenv(LK_TTS_CACHE_ENV, str(cache_dir))
    monkeypatch.setenv(LK_TTS_FFMPEG_ENV, str(ffmpeg_bin))

    monkeypatch.setattr(
        "localkoreantts.config.detect_ffmpeg_path",
        lambda explicit=None: ffmpeg_bin,
    )

    data = get_paths(redact=True)

    assert data["model_dir"].startswith("~/")
    assert data["cache_dir"].startswith("~/")
    assert data["ffmpeg_bin"].startswith("~/")
    assert data["env"][LK_TTS_MODEL_ENV] == str(model_dir)


def test_describe_environment_plain(monkeypatch, tmp_path):
    home = tmp_path / "home2"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    summary = describe_environment(redact=False)
    assert "platform=" in summary
    assert str(home) in summary
