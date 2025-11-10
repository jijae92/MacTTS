import pytest

from localkoreantts.engine import LocalKoreanTTSEngine, resolve_path_config


def test_engine_rejects_empty_text(tmp_path, monkeypatch):
    config = resolve_path_config()
    engine = LocalKoreanTTSEngine(path_config=config)
    with pytest.raises(ValueError):
        engine.synthesize_to_file("", "standard-female", tmp_path / "out.wav")
