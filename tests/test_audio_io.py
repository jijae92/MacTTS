from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from localkoreantts import audio_io
from localkoreantts.audio_io import (
    AudioPlaybackError,
    LK_TTS_SAMPLE_RATE_ENV,
    _coerce_to_float32,
    _resolve_sample_rate,
    _load_wave,
    play_wav,
)


def _write_silence(path: Path, samplerate: int = 22050) -> None:
    data = np.zeros((samplerate,), dtype=np.float32)
    sf.write(str(path), data, samplerate)


def test_play_wav_invokes_sounddevice(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path, samplerate=12345)

    calls = {"play": None, "wait": False}

    class DummySD:
        def play(self, data, samplerate=None, device=None):
            calls["play"] = {"samplerate": samplerate, "device": device, "size": len(data)}

        def wait(self):
            calls["wait"] = True

    monkeypatch.setattr(audio_io, "sd", DummySD())

    play_wav(wav_path, device="Built-in Output")

    assert calls["play"]["samplerate"] == 12345
    assert calls["play"]["device"] == "Built-in Output"
    assert calls["wait"] is True


def test_play_wav_respects_env_samplerate(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path, samplerate=16000)

    class DummySD:
        def __init__(self):
            self.used_rate = None

        def play(self, data, samplerate=None, device=None):
            self.used_rate = samplerate

        def wait(self):
            pass

    dummy = DummySD()
    monkeypatch.setattr(audio_io, "sd", dummy)
    monkeypatch.setenv(LK_TTS_SAMPLE_RATE_ENV, "44100")

    play_wav(wav_path)

    assert dummy.used_rate == 44100


def test_play_wav_skip_flag(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path)

    class DummySD:
        def play(self, *args, **kwargs):
            raise AssertionError("Should not be called")

        def wait(self):
            raise AssertionError("Should not be called")

    monkeypatch.setattr(audio_io, "sd", DummySD())

    play_wav(wav_path, skip_play=True)


def test_play_wav_errors_without_sounddevice(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path)
    monkeypatch.setattr(audio_io, "sd", None)

    with pytest.raises(AudioPlaybackError):
        play_wav(wav_path)


def test_play_wav_missing_file():
    with pytest.raises(AudioPlaybackError):
        play_wav("does-not-exist.wav")


def test_play_wav_invalid_samplerate_env(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path)
    monkeypatch.setenv(LK_TTS_SAMPLE_RATE_ENV, "not-a-number")

    with pytest.raises(AudioPlaybackError):
        play_wav(wav_path)


def test_load_wave_without_backends(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    _write_silence(wav_path)
    monkeypatch.setattr(audio_io, "sf", None)
    monkeypatch.setattr(audio_io, "scipy_wavfile", None)

    with pytest.raises(AudioPlaybackError):
        _load_wave(wav_path)


def test_load_wave_with_scipy(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(b"\x00\x00")
    monkeypatch.setattr(audio_io, "sf", None)

    class DummyReader:
        @staticmethod
        def read(path):
            return 11025, np.array([0, 1], dtype=np.int16)

    monkeypatch.setattr(audio_io, "scipy_wavfile", DummyReader)
    data, rate = _load_wave(wav_path)
    assert rate == 11025
    assert data.dtype == np.float32


def test_coerce_to_float32_from_int():
    data = np.array([0, 32767, -32768], dtype=np.int16)
    converted = _coerce_to_float32(data)
    assert converted.dtype == np.float32
    assert converted.max() <= 1.0


def test_coerce_to_float32_passthrough():
    data = np.array([0.1, 0.2], dtype=np.float32)
    assert np.array_equal(_coerce_to_float32(data), data)


def test_resolve_sample_rate_requires_value(monkeypatch):
    monkeypatch.delenv(LK_TTS_SAMPLE_RATE_ENV, raising=False)
    with pytest.raises(AudioPlaybackError):
        _resolve_sample_rate(explicit=None, fallback=None)


def test_resolve_sample_rate_explicit():
    assert _resolve_sample_rate(explicit=24000, fallback=None) == 24000
