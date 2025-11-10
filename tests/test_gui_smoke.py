import os
import sys
from pathlib import Path

import pytest

from localkoreantts.engine import VoiceProfile
from localkoreantts.gui import LocalKoreanTTSWindow
from localkoreantts.paths import PathConfig


pytestmark = pytest.mark.skipif(
    sys.platform.startswith("linux") and not os.environ.get("DISPLAY"),
    reason="GUI smoke test skipped on headless Linux (no display server).",
)


class _StubEngine:
    def __init__(self, *, path_config: PathConfig) -> None:
        self.path_config = path_config
        self.ffmpeg_path = None
        self._voices = [
            VoiceProfile(name="standard-female", locale="ko-KR", sample_rate=22050),
            VoiceProfile(name="lite", locale="ko-KR", sample_rate=16000),
        ]
        self.calls = []

    def voices(self):
        return list(self._voices)

    def synthesize_to_file(self, text: str, voice_name: str, output_path: Path) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"RIFF0000")
        self.calls.append({"text": text, "voice": voice_name, "path": destination})
        return destination


def test_gui_smoke_roundtrip(tmp_path, qtbot, monkeypatch):
    config = PathConfig(model_dir=tmp_path / "models", cache_dir=tmp_path / "cache").ensure()
    stub_engine = _StubEngine(path_config=config)

    monkeypatch.setattr(LocalKoreanTTSWindow, "_show_info", lambda *_, **__: None)
    monkeypatch.setattr(LocalKoreanTTSWindow, "_show_warning", lambda *_, **__: None)
    monkeypatch.setattr(LocalKoreanTTSWindow, "_show_error", lambda *_, **__: None)

    window = LocalKoreanTTSWindow(
        engine_factory=lambda **kwargs: stub_engine,
        path_config=config,
    )
    qtbot.addWidget(window)

    assert window._tabs.count() == 2
    assert window._tabs.tabText(0) == "Synthesis"
    assert window._tabs.tabText(1) == "Settings"
    assert window.voice_combo.count() == len(stub_engine.voices())
    assert not window.generate_btn.isEnabled()

    output_file = tmp_path / "artifacts" / "gui_out.wav"
    long_text = "GUI 입력 필드\n\n파일 선택 후 합성 버튼 활성화 여부 검증"
    window.output_edit.setText(str(output_file))
    window.text_edit.setPlainText(long_text)

    qtbot.waitUntil(lambda: window.generate_btn.isEnabled(), timeout=2000)

    window._handle_generate()
    assert output_file.exists()
    assert stub_engine.calls
    assert stub_engine.calls[0]["text"] == long_text

    logs = window.log_view.toPlainText()
    assert "Ready to synthesize" in logs
    assert "ffmpeg" in logs.lower()
    assert str(output_file) in logs

    window._tabs.setCurrentIndex(1)
    assert window.model_path_edit.text() == str(config.model_dir)
    assert window.ffmpeg_path_edit.text() == ""

    window.close()
