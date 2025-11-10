from localkoreantts import paths
from localkoreantts.paths import (
    LK_TTS_CACHE_ENV,
    LK_TTS_MODEL_ENV,
    describe_environment,
    resolve_path_config,
)


def test_env_overrides(monkeypatch, tmp_path):
    model_dir = tmp_path / "models"
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv(LK_TTS_MODEL_ENV, str(model_dir))
    monkeypatch.setenv(LK_TTS_CACHE_ENV, str(cache_dir))

    config = resolve_path_config()

    assert config.model_dir == model_dir
    assert config.cache_dir == cache_dir
    assert model_dir.exists()
    assert cache_dir.exists()


def test_default_paths_follow_spec(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / ".cache"))
    monkeypatch.delenv(LK_TTS_MODEL_ENV, raising=False)
    monkeypatch.delenv(LK_TTS_CACHE_ENV, raising=False)

    config = resolve_path_config()

    assert str(config.model_dir).endswith("localkoreantts/model")
    assert str(config.cache_dir).endswith("localkoreantts")


def test_windows_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, "_SYSTEM", "Windows")
    fake_appdata = tmp_path / "AppData" / "Local"
    fake_appdata.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(fake_appdata))
    monkeypatch.delenv(LK_TTS_MODEL_ENV, raising=False)
    monkeypatch.delenv(LK_TTS_CACHE_ENV, raising=False)

    config = resolve_path_config()

    assert "localkoreantts/model" in str(config.model_dir).lower()
    assert "localkoreantts/cache" in str(config.cache_dir).lower()


def test_paths_describe_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / ".cache"))
    summary = describe_environment()
    assert "platform=" in summary
