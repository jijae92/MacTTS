import os
import sys
from unittest import mock

import pytest
from PySide6.QtWidgets import QApplication

from localkoreantts.engine import VoiceProfile
from localkoreantts.gui import LocalKoreanTTSWindow
from localkoreantts.paths import PathConfig


pytestmark = pytest.mark.skipif(
    sys.platform.startswith("linux") and not os.environ.get("DISPLAY"),
    reason="GUI tests skipped on headless Linux (no display server).",
)


def test_gui_generate_invokes_engine(tmp_path):
    _app = QApplication.instance() or QApplication([])

    fake_engine = mock.MagicMock()
    fake_engine.voices.return_value = [
        VoiceProfile(name="test", locale="ko-KR", sample_rate=16000)
    ]
    fake_engine.synthesize_to_file.return_value = tmp_path / "out.wav"
    fake_engine.ffmpeg_path = None

    config = PathConfig(model_dir=tmp_path / "models", cache_dir=tmp_path / "cache").ensure()

    window = LocalKoreanTTSWindow(
        engine_factory=lambda **kwargs: fake_engine,
        path_config=config,
    )
    window._show_info = lambda *_, **__: None
    window._show_warning = lambda *_, **__: None
    window._show_error = lambda *_, **__: None

    assert "ffmpeg" in window.log_view.toPlainText().lower()

    window.text_edit.setPlainText("sample text")
    window.output_edit.setText(str(tmp_path / "result.wav"))

    window._handle_generate()

    fake_engine.synthesize_to_file.assert_called_once()
    window.close()
