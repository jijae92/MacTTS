from pathlib import Path

import pytest

from localkoreantts.ffmpeg import (
    LK_TTS_FFMPEG_ENV,
    detect_ffmpeg_path,
    describe_ffmpeg,
    find_ffmpeg,
)


def _make_exec(path: Path) -> Path:
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


def test_detect_ffmpeg_prefers_path(monkeypatch, tmp_path):
    path_binary = _make_exec(tmp_path / "from_path")
    env_binary = _make_exec(tmp_path / "from_env")

    monkeypatch.setenv(LK_TTS_FFMPEG_ENV, str(env_binary))
    monkeypatch.setattr(
        "localkoreantts.ffmpeg.shutil.which",
        lambda _: str(path_binary),
    )
    monkeypatch.setattr("localkoreantts.ffmpeg.COMMON_MAC_PATHS", ())

    detected = detect_ffmpeg_path()
    assert detected == path_binary


def test_detect_ffmpeg_uses_env_when_path_missing(monkeypatch, tmp_path):
    env_binary = _make_exec(tmp_path / "env_ffmpeg")
    monkeypatch.setenv(LK_TTS_FFMPEG_ENV, str(env_binary))
    monkeypatch.setattr("localkoreantts.ffmpeg.shutil.which", lambda _: None)
    monkeypatch.setattr("localkoreantts.ffmpeg.COMMON_MAC_PATHS", ())

    detected = detect_ffmpeg_path()
    assert detected == env_binary


def test_detect_ffmpeg_none_when_missing(monkeypatch):
    monkeypatch.delenv(LK_TTS_FFMPEG_ENV, raising=False)
    monkeypatch.setattr("localkoreantts.ffmpeg.shutil.which", lambda _: None)
    monkeypatch.setattr("localkoreantts.ffmpeg.COMMON_MAC_PATHS", ())
    assert detect_ffmpeg_path() is None


def test_detect_ffmpeg_uses_common_paths(monkeypatch, tmp_path):
    monkeypatch.setattr("localkoreantts.ffmpeg.shutil.which", lambda _: None)
    monkeypatch.delenv(LK_TTS_FFMPEG_ENV, raising=False)
    common_bin = _make_exec(tmp_path / "common_ffmpeg")
    monkeypatch.setattr("localkoreantts.ffmpeg.COMMON_MAC_PATHS", (str(common_bin),))
    detected = detect_ffmpeg_path()
    assert detected == common_bin


def test_find_ffmpeg_errors_for_invalid_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_ffmpeg(str(tmp_path / "missing"))


def test_describe_ffmpeg(monkeypatch, tmp_path):
    binary = _make_exec(tmp_path / "ffmpeg")
    binary.write_text("#!/bin/sh\necho ffmpeg version test\n")
    output = describe_ffmpeg(binary)
    assert "ffmpeg version" in output


def test_detect_ffmpeg_explicit_success(tmp_path):
    binary = _make_exec(tmp_path / "explicit_ffmpeg")
    detected = detect_ffmpeg_path(str(binary))
    assert detected == binary
