import pytest

from localkoreantts.models import ModelNotReadyError, ensure_model_ready
from localkoreantts.paths import PathConfig


def test_ensure_model_ready_missing_dir(tmp_path):
    config = PathConfig(model_dir=tmp_path / "missing", cache_dir=tmp_path / "cache")
    with pytest.raises(ModelNotReadyError):
        ensure_model_ready(config)


def test_ensure_model_ready_empty_dir(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    config = PathConfig(model_dir=model_dir, cache_dir=tmp_path / "cache")
    with pytest.raises(ModelNotReadyError):
        ensure_model_ready(config)
