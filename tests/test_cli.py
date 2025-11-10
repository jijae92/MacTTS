import json
from pathlib import Path

import pytest

from localkoreantts import cli
from localkoreantts.models import ModelNotReadyError
from localkoreantts.paths import LK_TTS_CACHE_ENV, LK_TTS_MODEL_ENV


@pytest.fixture(autouse=True)
def _mock_cli_ffmpeg(monkeypatch, tmp_path_factory):
    fake_ffmpeg = tmp_path_factory.mktemp("cli-ffmpeg") / "ffmpeg"
    fake_ffmpeg.write_text("#!/bin/sh\nexit 0\n")
    fake_ffmpeg.chmod(0o755)
    monkeypatch.setattr(cli, "describe_ffmpeg", lambda path: "ffmpeg=mocked")
    monkeypatch.setattr(cli, "detect_ffmpeg_path", lambda explicit=None: fake_ffmpeg)


def test_cli_generates_wave(tmp_path, monkeypatch):
    model_dir, cache_dir, destination, input_file = _prepare_cli_io(tmp_path, monkeypatch)

    exit_code = cli.main(
        [
            "--in",
            str(input_file),
            "--out",
            str(destination),
            "--voice",
            "lite",
            "--lang",
            "ko-KR",
            "--speed",
            "1.25",
        ]
    )
    assert exit_code == 0
    assert destination.exists()
    meta_path = destination.with_name(destination.stem + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["voice"] == "lite"
    assert meta["speed"] == 1.25
    assert meta["lang"] == "ko-KR"


def test_cli_describe_lists_environment(tmp_path, monkeypatch, capsys):
    model_dir, cache_dir, destination, _ = _prepare_cli_io(tmp_path, monkeypatch)

    exit_code = cli.main(
        [
            "--text",
            "테스트",
            "--out",
            str(destination),
            "--describe",
        ]
    )

    captured = capsys.readouterr()
    assert "platform=" in captured.out
    assert str(model_dir) in captured.out
    assert exit_code == 0


def test_cli_list_voices(tmp_path, monkeypatch, capsys):
    _prepare_cli_io(tmp_path, monkeypatch)
    exit_code = cli.main(["--list-voices"])
    out = capsys.readouterr().out
    assert "standard-female" in out
    assert exit_code == 0


def test_cli_play_invokes_audio(tmp_path, monkeypatch):
    _, _, destination, input_file = _prepare_cli_io(tmp_path, monkeypatch)
    played = {"called": False}

    monkeypatch.setattr(
        cli,
        "play_wav",
        lambda *args, **kwargs: played.__setitem__("called", True),
    )

    exit_code = cli.main(
        ["--in", str(input_file), "--out", str(destination), "--play"]
    )

    assert exit_code == 0
    assert played["called"] is True


def test_cli_model_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(LK_TTS_MODEL_ENV, str(tmp_path / "missing"))
    monkeypatch.setenv(LK_TTS_CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "ensure_model_ready", lambda config: (_ for _ in ()).throw(ModelNotReadyError("nope")))

    exit_code = cli.main(["--text", "hi", "--out", "ignored.wav"])
    captured = capsys.readouterr()
    assert "Model error" in captured.err
    assert exit_code == 2


def test_cli_warns_when_ffmpeg_missing(tmp_path, monkeypatch, capsys):
    _prepare_cli_io(tmp_path, monkeypatch)

    def boom(explicit=None):
        raise FileNotFoundError("boom")

    monkeypatch.setattr(cli, "detect_ffmpeg_path", boom)

    exit_code = cli.main(["--text", "hi", "--out", str(tmp_path / "sample.wav")])
    err = capsys.readouterr().err
    assert "FFmpeg notice" in err
    assert exit_code == 0


def test_cli_requires_text(tmp_path, monkeypatch):
    _, _, destination, _ = _prepare_cli_io(tmp_path, monkeypatch)
    with pytest.raises(SystemExit):
        cli.main(["--out", str(destination)])


def test_entry_point_wraps_main(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda argv=None: 0)
    with pytest.raises(SystemExit) as exc:
        cli.entry_point()
    assert exc.value.code == 0


def _prepare_cli_io(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    cache_dir = tmp_path / "cache"
    model_dir.mkdir()
    cache_dir.mkdir()
    (model_dir / "dummy.bin").write_text("x", encoding="utf-8")
    monkeypatch.setenv(LK_TTS_MODEL_ENV, str(model_dir))
    monkeypatch.setenv(LK_TTS_CACHE_ENV, str(cache_dir))
    destination = tmp_path / "sample.wav"
    input_file = tmp_path / "input.txt"
    input_file.write_text("테스트", encoding="utf-8")
    return model_dir, cache_dir, destination, input_file
