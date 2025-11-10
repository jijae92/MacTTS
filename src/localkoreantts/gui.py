"""PySide6 GUI tailored for macOS and cross-platform use.

Referenced by README "macOS → 3. Run CLI & GUI" and "GUI usage"; packaging flow
is detailed under "macOS packaging" and ARCHITECTURE.md.
"""

from __future__ import annotations

import sys
import os
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict

from PySide6 import QtCore, QtGui, QtWidgets

from .cli import _voice_lines
from .engine import LocalKoreanTTSEngine
from .paths import PathConfig, resolve_path_config

IS_MAC = sys.platform == "darwin"


# Background synthesis worker thread
class SynthesisWorker(QtCore.QThread):
    """Background worker for TTS synthesis to prevent UI freezing."""

    progress = QtCore.Signal(int, str)  # progress value, status message
    finished = QtCore.Signal(Path)  # output path
    error = QtCore.Signal(str)  # error message

    def __init__(
        self,
        engine: LocalKoreanTTSEngine,
        text: str,
        voice_name: str,
        output_path: Path,
        speed: float = 1.0
    ):
        super().__init__()
        self.engine = engine
        self.text = text
        self.voice_name = voice_name
        self.output_path = output_path
        self.speed = speed

    def run(self):
        """Execute synthesis in background thread."""
        try:
            self.progress.emit(10, "텍스트 준비 중...")
            QtCore.QThread.msleep(100)

            self.progress.emit(30, "음성 합성 중...")
            result = self.engine.synthesize_to_file(
                text=self.text,
                voice_name=self.voice_name,
                output_path=self.output_path,
                speed=self.speed
            )

            self.progress.emit(90, "파일 저장 중...")
            QtCore.QThread.msleep(100)

            self.progress.emit(100, "완료!")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


# Dialog synthesis worker thread
class DialogSynthesisWorker(QtCore.QThread):
    """Background worker for dialog synthesis."""

    progress = QtCore.Signal(int, str)
    finished = QtCore.Signal(Path)
    error = QtCore.Signal(str)

    def __init__(
        self,
        script_text: str,
        output_path: Path,
        speaker_config: Dict,
        audio_settings: Dict
    ):
        super().__init__()
        self.script_text = script_text
        self.output_path = output_path
        self.speaker_config = speaker_config
        self.audio_settings = audio_settings

    def run(self):
        """Execute dialog synthesis in background thread."""
        try:
            # Import dialog-tts modules
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dialog-tts"))
            from dialog_tts import DialogTTSEngine, SpeakerConfig, apply_speaker_name_mapping

            self.progress.emit(10, "화자 설정 중...")

            # Create speaker map
            speaker_map = {}

            # Speaker A
            config_a = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_config['voice_a'],
                'rate_wpm': self.speaker_config['rate_a'],
                'gain_db': 0.0,
                'pan': self.speaker_config['pan_a'],
                'aliases': []
            }
            speaker_map['A'] = SpeakerConfig(config_a, engine='edge')

            # Speaker B
            config_b = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_config['voice_b'],
                'rate_wpm': self.speaker_config['rate_b'],
                'gain_db': 0.0,
                'pan': self.speaker_config['pan_b'],
                'aliases': []
            }
            speaker_map['B'] = SpeakerConfig(config_b, engine='edge')

            # Apply custom names if provided
            custom_names = []
            if self.speaker_config.get('name_a'):
                custom_names.append(self.speaker_config['name_a'])
            if self.speaker_config.get('name_b'):
                custom_names.append(self.speaker_config['name_b'])

            if custom_names:
                speaker_map = apply_speaker_name_mapping(speaker_map, custom_names)

            self.progress.emit(25, "TTS 엔진 초기화 중...")

            # Initialize engine
            engine = DialogTTSEngine(
                engine='edge',
                sample_rate=self.audio_settings['sample_rate'],
                stereo=self.audio_settings['stereo']
            )

            self.progress.emit(35, "스크립트 준비 중...")

            # Save script to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(self.script_text)
                script_path = Path(f.name)

            try:
                self.progress.emit(40, "대화 합성 중... (시간이 걸릴 수 있습니다)")

                # Synthesize
                engine.synthesize_dialog(
                    script_path=script_path,
                    speaker_map=speaker_map,
                    output_path=self.output_path,
                    gap_ms=self.audio_settings['gap_ms'],
                    xfade_ms=20,
                    breath_ms=80,
                    normalize_dbfs=-1.0
                )

                self.progress.emit(95, "파일 저장 중...")
                QtCore.QThread.msleep(100)

                self.progress.emit(100, "완료!")
                self.finished.emit(self.output_path)

            finally:
                script_path.unlink(missing_ok=True)

        except Exception as e:
            self.error.emit(str(e))

# Modern UI stylesheet
MODERN_STYLESHEET = """
QMainWindow {
    background-color: #f5f5f5;
}

QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: white;
    padding: 10px;
}

QTabBar::tab {
    background: #e8e8e8;
    border: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 11pt;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: white;
    color: #2196F3;
}

QTabBar::tab:hover {
    background: #d0d0d0;
}

QGroupBox {
    font-size: 11pt;
    font-weight: 600;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background: #fafafa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    color: #2196F3;
}

QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 10px 24px;
    border-radius: 6px;
    font-size: 11pt;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}

QPushButton#browseButton {
    background-color: #757575;
    padding: 8px 16px;
}

QPushButton#browseButton:hover {
    background-color: #616161;
}

QPushButton#generateButton {
    background-color: #4CAF50;
    font-size: 12pt;
    padding: 12px 32px;
    min-height: 25px;
}

QPushButton#generateButton:hover {
    background-color: #45a049;
}

QPushButton#playButton {
    background-color: #FF9800;
    padding: 8px 16px;
}

QPushButton#playButton:hover {
    background-color: #F57C00;
}

QTextEdit, QPlainTextEdit {
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
    background: white;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #2196F3;
}

QLineEdit {
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    padding: 8px;
    font-size: 10pt;
    background: white;
}

QLineEdit:focus {
    border: 2px solid #2196F3;
}

QComboBox {
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 10pt;
    background: white;
    min-width: 100px;
}

QComboBox:hover {
    border: 2px solid #2196F3;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QSpinBox, QDoubleSpinBox {
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    padding: 6px;
    font-size: 10pt;
    background: white;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #2196F3;
}

QSlider::groove:horizontal {
    border: 1px solid #BDBDBD;
    height: 6px;
    background: #E0E0E0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #2196F3;
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #1976D2;
}

QProgressBar {
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    text-align: center;
    font-size: 10pt;
    font-weight: 500;
    background: white;
    min-height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4CAF50, stop:1 #8BC34A);
    border-radius: 4px;
}

QLabel {
    font-size: 10pt;
    color: #424242;
}

QLabel#titleLabel {
    font-size: 14pt;
    font-weight: bold;
    color: #1976D2;
}

QLabel#subtitleLabel {
    font-size: 11pt;
    font-weight: 600;
    color: #757575;
}

QLabel#infoLabel {
    font-size: 9pt;
    color: #757575;
    font-style: italic;
}

QCheckBox {
    font-size: 10pt;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #BDBDBD;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    border-color: #2196F3;
}

QStatusBar {
    background: #fafafa;
    border-top: 1px solid #e0e0e0;
    font-size: 9pt;
    padding: 4px;
}
"""

# Dark mode stylesheet
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    background: #2d2d2d;
    padding: 10px;
}

QTabBar::tab {
    background: #3c3c3c;
    border: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 11pt;
    font-weight: 500;
    color: #e0e0e0;
}

QTabBar::tab:selected {
    background: #2d2d2d;
    color: #42a5f5;
}

QTabBar::tab:hover {
    background: #4a4a4a;
}

QGroupBox {
    font-size: 11pt;
    font-weight: 600;
    border: 2px solid #3c3c3c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background: #252525;
    color: #e0e0e0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    color: #42a5f5;
}

QPushButton {
    background-color: #1976D2;
    color: white;
    border: none;
    padding: 10px 24px;
    border-radius: 6px;
    font-size: 11pt;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #2196F3;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #424242;
    color: #757575;
}

QPushButton#browseButton {
    background-color: #616161;
    padding: 8px 16px;
}

QPushButton#browseButton:hover {
    background-color: #757575;
}

QPushButton#generateButton {
    background-color: #388E3C;
    font-size: 12pt;
    padding: 12px 32px;
    min-height: 25px;
}

QPushButton#generateButton:hover {
    background-color: #4CAF50;
}

QPushButton#playButton {
    background-color: #F57C00;
    padding: 8px 16px;
}

QPushButton#playButton:hover {
    background-color: #FF9800;
}

QTextEdit, QPlainTextEdit {
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
    background: #2d2d2d;
    color: #e0e0e0;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #42a5f5;
}

QLineEdit {
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    padding: 8px;
    font-size: 10pt;
    background: #2d2d2d;
    color: #e0e0e0;
}

QLineEdit:focus {
    border: 2px solid #42a5f5;
}

QComboBox {
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 10pt;
    background: #2d2d2d;
    color: #e0e0e0;
    min-width: 100px;
}

QComboBox:hover {
    border: 2px solid #42a5f5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #42a5f5;
    border: 1px solid #3c3c3c;
}

QSpinBox, QDoubleSpinBox {
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    padding: 6px;
    font-size: 10pt;
    background: #2d2d2d;
    color: #e0e0e0;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #42a5f5;
}

QSlider::groove:horizontal {
    border: 1px solid #424242;
    height: 6px;
    background: #3c3c3c;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #42a5f5;
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #2196F3;
}

QProgressBar {
    border: 2px solid #3c3c3c;
    border-radius: 6px;
    text-align: center;
    font-size: 10pt;
    font-weight: 500;
    background: #2d2d2d;
    color: #e0e0e0;
    min-height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #388E3C, stop:1 #66BB6A);
    border-radius: 4px;
}

QLabel {
    font-size: 10pt;
    color: #e0e0e0;
}

QLabel#titleLabel {
    font-size: 14pt;
    font-weight: bold;
    color: #42a5f5;
}

QLabel#subtitleLabel {
    font-size: 11pt;
    font-weight: 600;
    color: #9e9e9e;
}

QLabel#infoLabel {
    font-size: 9pt;
    color: #9e9e9e;
    font-style: italic;
}

QCheckBox {
    font-size: 10pt;
    spacing: 8px;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #757575;
    background: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #42a5f5;
    border-color: #42a5f5;
}

QStatusBar {
    background: #252525;
    border-top: 1px solid #3c3c3c;
    font-size: 9pt;
    padding: 4px;
    color: #e0e0e0;
}

QScrollBar:vertical {
    background: #2d2d2d;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #616161;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #757575;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #2d2d2d;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background: #616161;
    border-radius: 6px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #757575;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


def _is_dark_mode() -> bool:
    """Detect if system is in dark mode."""
    try:
        # macOS dark mode detection
        if IS_MAC:
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and 'Dark' in result.stdout

        # Linux/Windows: Try to detect from Qt palette
        app = QtWidgets.QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QtGui.QPalette.Window)
            # If background is dark (luminance < 128)
            return bg_color.lightness() < 128
    except:
        pass

    return False


# Import dialog-tts modules if available
_DIALOG_TTS_AVAILABLE = False
try:
    # Add dialog-tts directory to path
    dialog_tts_dir = Path(__file__).parent.parent.parent / "dialog-tts"
    if dialog_tts_dir.exists():
        sys.path.insert(0, str(dialog_tts_dir))
        from dialog_tts import DialogTTSEngine, SpeakerConfig, apply_speaker_name_mapping
        from backends.edge_tts_backend import EdgeTTSBackend, EDGE_TTS_AVAILABLE
        _DIALOG_TTS_AVAILABLE = True
except Exception as e:
    print(f"Note: Dialog-TTS features not available: {e}")


class LocalKoreanTTSWindow(QtWidgets.QMainWindow):
    """Modern GUI for Korean TTS with enhanced UX."""

    def __init__(
        self,
        engine_factory: Callable[..., LocalKoreanTTSEngine] | None = None,
        path_config: PathConfig | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("🎙️ Local Korean TTS")
        self.setMinimumSize(900, 700)

        # Apply stylesheet based on system theme
        if _is_dark_mode():
            self.setStyleSheet(DARK_STYLESHEET)
        else:
            self.setStyleSheet(MODERN_STYLESHEET)

        self._engine_factory = engine_factory or LocalKoreanTTSEngine
        self._config = (path_config or resolve_path_config()).ensure()
        self._engine = self._build_engine()

        # Track last generated file for playback
        self._last_output_file: Optional[Path] = None

        self.text_edit: QtWidgets.QTextEdit
        self.voice_combo: QtWidgets.QComboBox
        self.output_edit: QtWidgets.QLineEdit
        self.generate_btn: QtWidgets.QPushButton
        self.progress_bar: QtWidgets.QProgressBar
        self.log_view: QtWidgets.QPlainTextEdit
        self.model_path_edit: QtWidgets.QLineEdit
        self.ffmpeg_path_edit: QtWidgets.QLineEdit

        # Worker threads
        self._synthesis_worker: Optional[SynthesisWorker] = None
        self._dialog_worker: Optional[DialogSynthesisWorker] = None

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_synthesis_tab(), "🎤 혼자 말하기")
        if _DIALOG_TTS_AVAILABLE:
            self._tabs.addTab(self._build_dialog_tab(), "💬 대화 형식")
        self._tabs.addTab(self._build_settings_tab(), "⚙️ 설정")
        self.setCentralWidget(self._tabs)

        self._setup_menu_bar()
        self._setup_status_bar()
        self._append_log("✓ 준비 완료")
        self._notify_ffmpeg_missing()

    def _build_engine(self) -> LocalKoreanTTSEngine:
        try:
            return self._engine_factory(path_config=self._config)
        except TypeError:
            return self._engine_factory()

    def _build_synthesis_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Input text group
        input_group = QtWidgets.QGroupBox("📝 Input Text")
        input_layout = QtWidgets.QVBoxLayout(input_group)

        # Character counter header
        counter_layout = QtWidgets.QHBoxLayout()
        counter_layout.addStretch()
        self.char_counter = QtWidgets.QLabel("0 characters")
        self.char_counter.setObjectName("infoLabel")
        counter_layout.addWidget(self.char_counter)
        input_layout.addLayout(counter_layout)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setPlaceholderText("여기에 합성할 텍스트를 입력하세요...")
        self.text_edit.setMinimumHeight(150)
        self.text_edit.textChanged.connect(self._update_generate_enabled)
        self.text_edit.textChanged.connect(self._update_char_count)
        self.text_edit.setToolTip("합성할 한국어 텍스트를 입력하세요")
        input_layout.addWidget(self.text_edit)

        layout.addWidget(input_group)

        # Voice and speed settings group
        settings_group = QtWidgets.QGroupBox("🎛️ Voice Settings")
        settings_layout = QtWidgets.QGridLayout(settings_group)
        settings_layout.setSpacing(12)

        # Voice selection
        settings_layout.addWidget(QtWidgets.QLabel("Voice:"), 0, 0)
        self.voice_combo = QtWidgets.QComboBox()
        self.voice_combo.addItems([v.name for v in self._engine.voices()])
        self.voice_combo.setToolTip("음성 선택")
        settings_layout.addWidget(self.voice_combo, 0, 1)

        # Speed control
        settings_layout.addWidget(QtWidgets.QLabel("Speed:"), 1, 0)
        speed_widget = QtWidgets.QWidget()
        speed_layout = QtWidgets.QHBoxLayout(speed_widget)
        speed_layout.setContentsMargins(0, 0, 0, 0)

        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(50, 200)  # 0.5x to 2.0x
        self.speed_slider.setValue(100)  # 1.0x default
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.setToolTip("말하기 속도 조절 (0.5x ~ 2.0x)")
        speed_layout.addWidget(self.speed_slider)

        self.speed_label = QtWidgets.QLabel("1.0x")
        self.speed_label.setMinimumWidth(50)
        self.speed_label.setAlignment(QtCore.Qt.AlignCenter)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v/100:.1f}x")
        )
        speed_layout.addWidget(self.speed_label)

        settings_layout.addWidget(speed_widget, 1, 1)

        layout.addWidget(settings_group)

        # Output file group
        output_group = QtWidgets.QGroupBox("💾 Output")
        output_layout = QtWidgets.QVBoxLayout(output_group)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(QtWidgets.QLabel("Output File:"))

        # Default to ~/Downloads/latest.wav
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        self.output_edit = QtWidgets.QLineEdit(str(downloads_dir / "latest.wav"))
        self.output_edit.textChanged.connect(self._update_generate_enabled)
        self.output_edit.setToolTip("출력 파일 경로")
        output_row.addWidget(self.output_edit)

        browse_btn = QtWidgets.QPushButton("📁 Browse...")
        browse_btn.setObjectName("browseButton")
        browse_btn.setToolTip("출력 파일 선택 (Cmd+O)")
        browse_btn.setShortcut(self._platform_shortcut("O"))
        browse_btn.clicked.connect(self._choose_output)
        output_row.addWidget(browse_btn)

        output_layout.addLayout(output_row)
        layout.addWidget(output_group)

        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)

        self.generate_btn = QtWidgets.QPushButton("🎵 Generate Audio")
        self.generate_btn.setObjectName("generateButton")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setToolTip("오디오 생성 (Cmd+G)")
        self.generate_btn.setShortcut(self._platform_shortcut("G"))
        self.generate_btn.clicked.connect(self._handle_generate)
        button_layout.addWidget(self.generate_btn, stretch=3)

        self.play_btn = QtWidgets.QPushButton("▶️ Play")
        self.play_btn.setObjectName("playButton")
        self.play_btn.setEnabled(False)
        self.play_btn.setToolTip("생성된 오디오 재생 (Cmd+P)")
        self.play_btn.setShortcut(self._platform_shortcut("P"))
        self.play_btn.clicked.connect(self._play_audio)
        button_layout.addWidget(self.play_btn, stretch=1)

        layout.addLayout(button_layout)

        # Add progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Log view
        log_label = QtWidgets.QLabel("📋 Log")
        log_label.setObjectName("subtitleLabel")
        layout.addWidget(log_label)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(self.log_view)

        return widget

    def _build_dialog_tab(self) -> QtWidgets.QWidget:
        """Build the multi-speaker dialog synthesis tab."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QtWidgets.QLabel("💬 두 화자 대화 합성")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Script input
        script_group = QtWidgets.QGroupBox("📝 대화 스크립트")
        script_layout = QtWidgets.QVBoxLayout(script_group)

        script_label = QtWidgets.QLabel("대화 내용을 입력하세요 (A:, B: 형식 사용):")
        script_layout.addWidget(script_label)

        self.dialog_script_text = QtWidgets.QPlainTextEdit()
        self.dialog_script_text.setPlaceholderText(
            "A: 안녕하세요. 오늘 일정 확인하셨어요?\n"
            "B: 네, 10시에 스탠드업 미팅이 있어요.\n\n"
            "[silence=400]\n\n"
            "A: 그 다음에는 보안 점검 보고서 리뷰가 있네요.\n"
            "B: 맞아요. 성능 테스트도 같이 검토해야 해요."
        )
        self.dialog_script_text.setMinimumHeight(150)
        script_layout.addWidget(self.dialog_script_text)
        layout.addWidget(script_group)

        # Speaker configuration
        speaker_group = QtWidgets.QGroupBox("🎤 화자 설정")
        speaker_layout = QtWidgets.QGridLayout(speaker_group)
        speaker_layout.setSpacing(10)

        # Speaker A header
        speaker_a_header = QtWidgets.QLabel("화자 A")
        speaker_a_header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #2196F3;")
        speaker_layout.addWidget(speaker_a_header, 0, 0, 1, 4)

        # Speaker A
        speaker_layout.addWidget(QtWidgets.QLabel("명칭:"), 1, 0)
        self.speaker_a_name = QtWidgets.QLineEdit()
        self.speaker_a_name.setPlaceholderText("예: 학생, 진행자, 홍길동")
        self.speaker_a_name.setToolTip("화자 A의 이름 (선택사항)")
        speaker_layout.addWidget(self.speaker_a_name, 1, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("목소리:"), 1, 2)
        self.speaker_a_voice = QtWidgets.QComboBox()
        self.speaker_a_voice.addItems(["SunHi", "JiMin", "SeoHyeon", "InJoon", "Hyunsu", "GookMin"])
        self.speaker_a_voice.setToolTip("화자 A의 TTS 목소리")
        speaker_layout.addWidget(self.speaker_a_voice, 1, 3)

        speaker_layout.addWidget(QtWidgets.QLabel("속도:"), 2, 0)
        self.speaker_a_rate = QtWidgets.QSpinBox()
        self.speaker_a_rate.setRange(100, 300)
        self.speaker_a_rate.setValue(180)
        self.speaker_a_rate.setSuffix(" WPM")
        self.speaker_a_rate.setToolTip("말하기 속도 (분당 단어 수)")
        speaker_layout.addWidget(self.speaker_a_rate, 2, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("패닝:"), 2, 2)
        self.speaker_a_pan = QtWidgets.QDoubleSpinBox()
        self.speaker_a_pan.setRange(-1.0, 1.0)
        self.speaker_a_pan.setSingleStep(0.1)
        self.speaker_a_pan.setValue(-0.3)
        self.speaker_a_pan.setToolTip("스테레오 위치: -1.0 (왼쪽) ~ +1.0 (오른쪽)")
        speaker_layout.addWidget(self.speaker_a_pan, 2, 3)

        # Separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        speaker_layout.addWidget(separator, 3, 0, 1, 4)

        # Speaker B header
        speaker_b_header = QtWidgets.QLabel("화자 B")
        speaker_b_header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #FF9800;")
        speaker_layout.addWidget(speaker_b_header, 4, 0, 1, 4)

        # Speaker B
        speaker_layout.addWidget(QtWidgets.QLabel("명칭:"), 5, 0)
        self.speaker_b_name = QtWidgets.QLineEdit()
        self.speaker_b_name.setPlaceholderText("예: 전문가, 게스트, 김철수")
        self.speaker_b_name.setToolTip("화자 B의 이름 (선택사항)")
        speaker_layout.addWidget(self.speaker_b_name, 5, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("목소리:"), 5, 2)
        self.speaker_b_voice = QtWidgets.QComboBox()
        self.speaker_b_voice.addItems(["InJoon", "Hyunsu", "GookMin", "SunHi", "JiMin", "SeoHyeon"])
        self.speaker_b_voice.setToolTip("화자 B의 TTS 목소리")
        speaker_layout.addWidget(self.speaker_b_voice, 5, 3)

        speaker_layout.addWidget(QtWidgets.QLabel("속도:"), 6, 0)
        self.speaker_b_rate = QtWidgets.QSpinBox()
        self.speaker_b_rate.setRange(100, 300)
        self.speaker_b_rate.setValue(170)
        self.speaker_b_rate.setSuffix(" WPM")
        self.speaker_b_rate.setToolTip("말하기 속도 (분당 단어 수)")
        speaker_layout.addWidget(self.speaker_b_rate, 6, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("패닝:"), 6, 2)
        self.speaker_b_pan = QtWidgets.QDoubleSpinBox()
        self.speaker_b_pan.setRange(-1.0, 1.0)
        self.speaker_b_pan.setSingleStep(0.1)
        self.speaker_b_pan.setValue(0.3)
        self.speaker_b_pan.setToolTip("스테레오 위치: -1.0 (왼쪽) ~ +1.0 (오른쪽)")
        speaker_layout.addWidget(self.speaker_b_pan, 6, 3)

        layout.addWidget(speaker_group)

        # Audio settings
        audio_group = QtWidgets.QGroupBox("Audio Settings")
        audio_layout = QtWidgets.QGridLayout(audio_group)

        self.dialog_stereo_check = QtWidgets.QCheckBox("Stereo Output (with panning)")
        self.dialog_stereo_check.setChecked(True)
        audio_layout.addWidget(self.dialog_stereo_check, 0, 0, 1, 2)

        audio_layout.addWidget(QtWidgets.QLabel("Gap (ms):"), 1, 0)
        self.dialog_gap_spin = QtWidgets.QSpinBox()
        self.dialog_gap_spin.setRange(0, 2000)
        self.dialog_gap_spin.setValue(250)
        audio_layout.addWidget(self.dialog_gap_spin, 1, 1)

        audio_layout.addWidget(QtWidgets.QLabel("Sample Rate:"), 1, 2)
        self.dialog_sr_combo = QtWidgets.QComboBox()
        self.dialog_sr_combo.addItems(["24000", "22050", "16000"])
        audio_layout.addWidget(self.dialog_sr_combo, 1, 3)

        layout.addWidget(audio_group)

        # Output
        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(QtWidgets.QLabel("Output File:"))
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        self.dialog_output_edit = QtWidgets.QLineEdit(str(downloads / "dialog.wav"))
        output_row.addWidget(self.dialog_output_edit)

        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._choose_dialog_output)
        output_row.addWidget(browse_btn)
        layout.addLayout(output_row)

        # Generate button
        self.dialog_generate_btn = QtWidgets.QPushButton("🎵 Generate Dialog Audio")
        self.dialog_generate_btn.setObjectName("generateButton")
        self.dialog_generate_btn.setToolTip("대화 오디오 생성")
        self.dialog_generate_btn.clicked.connect(self._handle_dialog_generate)
        layout.addWidget(self.dialog_generate_btn)

        # Progress bar
        self.dialog_progress_bar = QtWidgets.QProgressBar()
        self.dialog_progress_bar.setVisible(False)
        layout.addWidget(self.dialog_progress_bar)

        # Dialog log view
        self.dialog_log_view = QtWidgets.QPlainTextEdit()
        self.dialog_log_view.setReadOnly(True)
        self.dialog_log_view.setMaximumHeight(100)
        layout.addWidget(QtWidgets.QLabel("Log:"))
        layout.addWidget(self.dialog_log_view)

        # Wrap in scroll area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        return scroll_area

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.model_path_edit = QtWidgets.QLineEdit(str(self._config.model_dir))
        model_button = QtWidgets.QPushButton("Browse…")
        model_button.clicked.connect(self._choose_model_dir)
        model_row = self._row_widget(self.model_path_edit, model_button)
        layout.addRow("Model Directory", model_row)

        self.ffmpeg_path_edit = QtWidgets.QLineEdit(
            str(self._engine.ffmpeg_path) if self._engine.ffmpeg_path else ""
        )
        ffmpeg_button = QtWidgets.QPushButton("Browse…")
        ffmpeg_button.clicked.connect(self._choose_ffmpeg_path)
        ffmpeg_row = self._row_widget(self.ffmpeg_path_edit, ffmpeg_button)
        layout.addRow("FFmpeg Binary", ffmpeg_row)

        # Wrap in scroll area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        return scroll_area

    @staticmethod
    def _row_widget(edit: QtWidgets.QWidget, button: QtWidgets.QWidget) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(edit)
        h_layout.addWidget(button)
        return container

    def _setup_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        describe_action = QtGui.QAction("Describe Runtime", self)
        describe_action.setShortcut(self._platform_shortcut("D"))
        describe_action.triggered.connect(self._describe_runtime)
        file_menu.addAction(describe_action)

        open_model_action = QtGui.QAction("Open Model Directory", self)
        open_model_action.setShortcut(self._platform_shortcut("M"))
        open_model_action.triggered.connect(self._open_model_dir)
        file_menu.addAction(open_model_action)

        quit_action = QtGui.QAction("Quit", self)
        quit_action.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _choose_output(self) -> None:
        # Default to ~/Downloads
        downloads_dir = Path.home() / "Downloads"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Select output WAV",
            str(downloads_dir / "latest.wav"),
            "Wave files (*.wav)",
        )
        if path:
            self.output_edit.setText(path)

    def _choose_model_dir(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Model Directory",
            str(self._config.model_dir),
        )
        if directory:
            self.model_path_edit.setText(directory)
            self._config = PathConfig(
                model_dir=Path(directory),
                cache_dir=self._config.cache_dir,
            ).ensure()
            self._engine = self._build_engine()
            self._append_log(f"Model directory set to {directory}")

    def _choose_ffmpeg_path(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select FFmpeg Binary",
            self.ffmpeg_path_edit.text() or str(Path.home()),
        )
        if path:
            self.ffmpeg_path_edit.setText(path)
            self._engine.ffmpeg_path = Path(path)
            self._append_log(f"FFmpeg path set to {path}")

    def _open_model_dir(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self._config.model_dir)))

    def _setup_status_bar(self) -> None:
        """Setup status bar with useful information."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _update_char_count(self) -> None:
        """Update character counter."""
        text = self.text_edit.toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        self.char_counter.setText(f"{char_count} characters, {word_count} words")

        # Update status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"Text: {char_count} chars")

    def _play_audio(self) -> None:
        """Play the last generated audio file."""
        if not self._last_output_file or not self._last_output_file.exists():
            self._show_warning("No Audio", "생성된 오디오 파일이 없습니다.")
            return

        try:
            if IS_MAC:
                # macOS: use 'open' command
                subprocess.run(['open', str(self._last_output_file)], check=True)
            elif sys.platform == 'win32':
                # Windows: use 'start' command
                os.startfile(str(self._last_output_file))
            else:
                # Linux: use 'xdg-open'
                subprocess.run(['xdg-open', str(self._last_output_file)], check=True)

            self._append_log(f"▶️ Playing: {self._last_output_file.name}")
        except Exception as e:
            self._show_error("Playback Error", f"오디오 재생 실패: {e}")

    def _handle_generate(self) -> None:
        """Start synthesis in background thread."""
        text = self.text_edit.toPlainText().strip()
        if not text:
            self._show_warning("입력 필요", "합성할 텍스트를 입력하세요.")
            return
        destination_text = self.output_edit.text().strip()
        if not destination_text:
            self._show_warning("출력 파일 필요", "출력 파일을 선택하세요.")
            return
        destination = Path(destination_text).expanduser()

        # Prepare UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        self.play_btn.setEnabled(False)

        # Get parameters
        speed = self.speed_slider.value() / 100.0
        voice_name = self.voice_combo.currentText()

        self._append_log(f"합성 시작: {len(text)}자, 속도 {speed}x")

        # Create and start worker
        self._synthesis_worker = SynthesisWorker(
            engine=self._engine,
            text=text,
            voice_name=voice_name,
            output_path=destination,
            speed=speed
        )

        # Connect signals
        self._synthesis_worker.progress.connect(self._on_synthesis_progress)
        self._synthesis_worker.finished.connect(self._on_synthesis_finished)
        self._synthesis_worker.error.connect(self._on_synthesis_error)

        # Start worker
        self._synthesis_worker.start()

    def _on_synthesis_progress(self, value: int, message: str):
        """Update progress during synthesis."""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(message)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message)

    def _on_synthesis_finished(self, result_path: Path):
        """Handle successful synthesis completion."""
        self._append_log(f"✓ 완료: {result_path.name}")

        # Enable play button and store output file
        self._last_output_file = result_path
        self.play_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)

        # Update status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(f"✓ 생성 완료: {result_path.name}")

        self._show_info("성공", f"오디오가 성공적으로 생성되었습니다!\n\n저장 위치:\n{result_path}")

        # Hide progress bar after delay
        QtCore.QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))

    def _on_synthesis_error(self, error_message: str):
        """Handle synthesis error."""
        self._append_log(f"✗ 오류: {error_message}")
        self._show_error("합성 실패", f"오디오 생성 중 오류가 발생했습니다:\n\n{error_message}")

        self.generate_btn.setEnabled(True)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage("✗ 합성 실패")

        # Hide progress bar
        QtCore.QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))

    def _describe_runtime(self) -> None:
        lines = _voice_lines(self._engine.voices())
        self._show_info("Runtime Info", "\n".join(lines))

    def _show_info(self, title: str, message: str) -> None:
        QtWidgets.QMessageBox.information(self, title, message)

    def _show_warning(self, title: str, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, title, message)

    def _show_error(self, title: str, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, message)

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] {message}")
        self.log_view.ensureCursorVisible()
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

    def _update_generate_enabled(self) -> None:
        has_text = bool(self.text_edit.toPlainText().strip())
        has_output = bool(self.output_edit.text().strip())
        self.generate_btn.setEnabled(has_text and has_output)

    def _notify_ffmpeg_missing(self) -> None:
        # Check if ffmpeg is available
        import shutil
        if self._engine.ffmpeg_path or shutil.which('ffmpeg'):
            return

        # Show warning message
        message = (
            "⚠️  FFmpeg가 설치되지 않았습니다!\n\n"
            "FFmpeg가 없으면 실제 TTS 음성 대신 사인파 테스트 톤만 생성됩니다.\n\n"
            "FFmpeg 설치 방법:\n"
            "  • macOS: brew install ffmpeg\n"
            "  • Linux: sudo apt install ffmpeg\n"
            "  • Windows: ffmpeg.org에서 다운로드\n\n"
            "설치 후 GUI를 재시작하세요."
        )
        self._append_log("⚠️  FFmpeg not detected - TTS will not work!")

        # Show popup warning so users don't miss it
        QtWidgets.QMessageBox.warning(
            self,
            "FFmpeg 필요",
            message
        )

    def _platform_shortcut(self, key: str) -> QtGui.QKeySequence:
        modifier = "Meta+" if IS_MAC else "Ctrl+"
        return QtGui.QKeySequence(modifier + key)

    def _choose_dialog_output(self) -> None:
        """Choose output file for dialog synthesis."""
        downloads_dir = Path.home() / "Downloads"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Select output audio file",
            str(downloads_dir / "dialog.wav"),
            "Audio files (*.wav *.mp3)",
        )
        if path:
            self.dialog_output_edit.setText(path)

    def _dialog_log(self, message: str) -> None:
        """Add message to dialog log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.dialog_log_view.appendPlainText(f"[{timestamp}] {message}")
        self.dialog_log_view.ensureCursorVisible()
        QtWidgets.QApplication.processEvents()

    def _handle_dialog_generate(self) -> None:
        """Start dialog synthesis in background thread."""
        if not _DIALOG_TTS_AVAILABLE:
            self._show_error("Feature Unavailable", "Dialog-TTS features are not available.")
            return

        # Validate inputs
        script = self.dialog_script_text.toPlainText().strip()
        if not script:
            self._show_warning("Missing script", "Enter a dialog script to synthesize.")
            return

        output_text = self.dialog_output_edit.text().strip()
        if not output_text:
            self._show_warning("Missing output", "Select an output file.")
            return

        output_path = Path(output_text)
        if not output_path.parent.exists():
            self._show_warning("Invalid path", f"Output directory does not exist: {output_path.parent}")
            return

        # Prepare speaker config
        speaker_config = {
            'voice_a': self.speaker_a_voice.currentText(),
            'voice_b': self.speaker_b_voice.currentText(),
            'name_a': self.speaker_a_name.text().strip(),
            'name_b': self.speaker_b_name.text().strip(),
            'rate_a': self.speaker_a_rate.value(),
            'rate_b': self.speaker_b_rate.value(),
            'pan_a': self.speaker_a_pan.value(),
            'pan_b': self.speaker_b_pan.value(),
        }

        # Prepare audio settings
        audio_settings = {
            'sample_rate': int(self.dialog_sr_combo.currentText()),
            'stereo': self.dialog_stereo_check.isChecked(),
            'gap_ms': self.dialog_gap_spin.value(),
        }

        # Show progress and disable button
        self.dialog_progress_bar.setVisible(True)
        self.dialog_progress_bar.setRange(0, 100)
        self.dialog_progress_bar.setValue(0)
        self.dialog_generate_btn.setEnabled(False)
        self._dialog_log("대화 합성을 시작합니다...")

        # Create and start worker thread
        self._dialog_worker = DialogSynthesisWorker(
            script_text=script,
            output_path=output_path,
            speaker_config=speaker_config,
            audio_settings=audio_settings
        )
        self._dialog_worker.progress.connect(self._on_dialog_progress)
        self._dialog_worker.finished.connect(self._on_dialog_finished)
        self._dialog_worker.error.connect(self._on_dialog_error)
        self._dialog_worker.start()

    def _on_dialog_progress(self, value: int, message: str) -> None:
        """Handle dialog synthesis progress updates."""
        self.dialog_progress_bar.setValue(value)
        self.dialog_progress_bar.setFormat(f"{message} ({value}%)")
        self._dialog_log(message)

    def _on_dialog_finished(self, output_path: Path) -> None:
        """Handle dialog synthesis completion."""
        self._dialog_log(f"✓ 성공! 저장 위치: {output_path}")
        self.dialog_progress_bar.setValue(100)
        self.dialog_progress_bar.setFormat("완료!")

        # Re-enable button
        self.dialog_generate_btn.setEnabled(True)

        # Show success message
        self._show_info("완료", f"대화 오디오가 성공적으로 생성되었습니다!\n\n저장 위치:\n{output_path}")

        # Hide progress bar after delay
        QtCore.QTimer.singleShot(2000, lambda: self.dialog_progress_bar.setVisible(False))

    def _on_dialog_error(self, error_message: str) -> None:
        """Handle dialog synthesis errors."""
        self._dialog_log(f"✗ 오류: {error_message}")
        self.dialog_progress_bar.setFormat("오류 발생")
        self.dialog_generate_btn.setEnabled(True)
        self._show_error("생성 실패", error_message)

        # Hide progress bar after delay
        QtCore.QTimer.singleShot(2000, lambda: self.dialog_progress_bar.setVisible(False))


def run(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    app = _bootstrap_app(argv)
    window = LocalKoreanTTSWindow()
    window.show()
    return app.exec()


def entry_point() -> None:
    raise SystemExit(run())


def _bootstrap_app(argv: list[str]) -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app:
        return app
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(argv)
    app.setApplicationName("Local Korean TTS")
    app.setOrganizationName("LocalKoreanTTS")
    icon = app.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
    app.setWindowIcon(icon)
    return app
