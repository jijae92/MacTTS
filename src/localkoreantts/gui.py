"""PySide6 GUI tailored for macOS and cross-platform use.

Referenced by README "macOS → 3. Run CLI & GUI" and "GUI usage"; packaging flow
is detailed under "macOS packaging" and ARCHITECTURE.md.
"""

from __future__ import annotations

import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict

from PySide6 import QtCore, QtGui, QtWidgets

from .cli import _voice_lines
from .engine import LocalKoreanTTSEngine
from .paths import PathConfig, resolve_path_config

IS_MAC = sys.platform == "darwin"

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
    """Simple GUI that proxies the CLI workflow."""

    def __init__(
        self,
        engine_factory: Callable[..., LocalKoreanTTSEngine] | None = None,
        path_config: PathConfig | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Local Korean TTS")

        self._engine_factory = engine_factory or LocalKoreanTTSEngine
        self._config = (path_config or resolve_path_config()).ensure()
        self._engine = self._build_engine()

        self.text_edit: QtWidgets.QTextEdit
        self.voice_combo: QtWidgets.QComboBox
        self.output_edit: QtWidgets.QLineEdit
        self.generate_btn: QtWidgets.QPushButton
        self.progress_bar: QtWidgets.QProgressBar
        self.log_view: QtWidgets.QPlainTextEdit
        self.model_path_edit: QtWidgets.QLineEdit
        self.ffmpeg_path_edit: QtWidgets.QLineEdit

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_synthesis_tab(), "Single Speaker")
        if _DIALOG_TTS_AVAILABLE:
            self._tabs.addTab(self._build_dialog_tab(), "Multi-Speaker Dialog")
        self._tabs.addTab(self._build_settings_tab(), "Settings")
        self.setCentralWidget(self._tabs)

        self._setup_menu_bar()
        self._append_log("Ready to synthesize.")
        self._notify_ffmpeg_missing()

    def _build_engine(self) -> LocalKoreanTTSEngine:
        try:
            return self._engine_factory(path_config=self._config)
        except TypeError:
            return self._engine_factory()

    def _build_synthesis_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        layout.addWidget(QtWidgets.QLabel("Input Text"))
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.textChanged.connect(self._update_generate_enabled)
        layout.addWidget(self.text_edit)

        voice_row = QtWidgets.QHBoxLayout()
        voice_row.addWidget(QtWidgets.QLabel("Voice"))
        self.voice_combo = QtWidgets.QComboBox()
        self.voice_combo.addItems([v.name for v in self._engine.voices()])
        voice_row.addWidget(self.voice_combo)

        # Add speed control
        voice_row.addWidget(QtWidgets.QLabel("Speed"))
        self.speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed_slider.setRange(50, 200)  # 0.5x to 2.0x
        self.speed_slider.setValue(100)  # 1.0x default
        self.speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.setMaximumWidth(150)
        voice_row.addWidget(self.speed_slider)

        self.speed_label = QtWidgets.QLabel("1.0x")
        self.speed_label.setMinimumWidth(40)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v/100:.1f}x")
        )
        voice_row.addWidget(self.speed_label)

        layout.addLayout(voice_row)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(QtWidgets.QLabel("Output File"))
        # Default to ~/Downloads/latest.wav
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        self.output_edit = QtWidgets.QLineEdit(str(downloads_dir / "latest.wav"))
        self.output_edit.textChanged.connect(self._update_generate_enabled)
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._choose_output)
        output_row.addWidget(self.output_edit)
        output_row.addWidget(browse_btn)
        layout.addLayout(output_row)

        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._handle_generate)
        layout.addWidget(self.generate_btn)

        # Add progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        describe_btn = QtWidgets.QPushButton("Describe Runtime")
        describe_btn.clicked.connect(self._describe_runtime)
        layout.addWidget(describe_btn)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        return widget

    def _build_dialog_tab(self) -> QtWidgets.QWidget:
        """Build the multi-speaker dialog synthesis tab."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Title
        title = QtWidgets.QLabel("Multi-Speaker Dialog Synthesis")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Script input
        script_group = QtWidgets.QGroupBox("Dialog Script")
        script_layout = QtWidgets.QVBoxLayout(script_group)

        script_label = QtWidgets.QLabel("Enter your dialog (use A:, B: for speakers):")
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
        speaker_group = QtWidgets.QGroupBox("Speaker Configuration")
        speaker_layout = QtWidgets.QGridLayout(speaker_group)

        # Speaker A
        speaker_layout.addWidget(QtWidgets.QLabel("Speaker A Name:"), 0, 0)
        self.speaker_a_name = QtWidgets.QLineEdit()
        self.speaker_a_name.setPlaceholderText("학생")
        speaker_layout.addWidget(self.speaker_a_name, 0, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("Voice:"), 0, 2)
        self.speaker_a_voice = QtWidgets.QComboBox()
        self.speaker_a_voice.addItems(["SunHi", "JiMin", "SeoHyeon", "InJoon", "Hyunsu", "GookMin"])
        speaker_layout.addWidget(self.speaker_a_voice, 0, 3)

        speaker_layout.addWidget(QtWidgets.QLabel("Speed (WPM):"), 1, 0)
        self.speaker_a_rate = QtWidgets.QSpinBox()
        self.speaker_a_rate.setRange(100, 300)
        self.speaker_a_rate.setValue(180)
        speaker_layout.addWidget(self.speaker_a_rate, 1, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("Pan:"), 1, 2)
        self.speaker_a_pan = QtWidgets.QDoubleSpinBox()
        self.speaker_a_pan.setRange(-1.0, 1.0)
        self.speaker_a_pan.setSingleStep(0.1)
        self.speaker_a_pan.setValue(-0.3)
        speaker_layout.addWidget(self.speaker_a_pan, 1, 3)

        # Separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        speaker_layout.addWidget(separator, 2, 0, 1, 4)

        # Speaker B
        speaker_layout.addWidget(QtWidgets.QLabel("Speaker B Name:"), 3, 0)
        self.speaker_b_name = QtWidgets.QLineEdit()
        self.speaker_b_name.setPlaceholderText("전문가")
        speaker_layout.addWidget(self.speaker_b_name, 3, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("Voice:"), 3, 2)
        self.speaker_b_voice = QtWidgets.QComboBox()
        self.speaker_b_voice.addItems(["InJoon", "Hyunsu", "GookMin", "SunHi", "JiMin", "SeoHyeon"])
        speaker_layout.addWidget(self.speaker_b_voice, 3, 3)

        speaker_layout.addWidget(QtWidgets.QLabel("Speed (WPM):"), 4, 0)
        self.speaker_b_rate = QtWidgets.QSpinBox()
        self.speaker_b_rate.setRange(100, 300)
        self.speaker_b_rate.setValue(170)
        speaker_layout.addWidget(self.speaker_b_rate, 4, 1)

        speaker_layout.addWidget(QtWidgets.QLabel("Pan:"), 4, 2)
        self.speaker_b_pan = QtWidgets.QDoubleSpinBox()
        self.speaker_b_pan.setRange(-1.0, 1.0)
        self.speaker_b_pan.setSingleStep(0.1)
        self.speaker_b_pan.setValue(0.3)
        speaker_layout.addWidget(self.speaker_b_pan, 4, 3)

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
        self.dialog_generate_btn = QtWidgets.QPushButton("Generate Dialog Audio")
        self.dialog_generate_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-size: 12pt; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
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

        return widget

    def _build_settings_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)

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

        return widget

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

    def _handle_generate(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            self._show_warning("Missing text", "Enter text to synthesize.")
            return
        destination_text = self.output_edit.text().strip()
        if not destination_text:
            self._show_warning("Missing output", "Select an output file.")
            return
        destination = Path(destination_text).expanduser()

        # Show progress bar and disable button
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing...")
        self.generate_btn.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        try:
            # Update progress: preparing
            self.progress_bar.setValue(10)
            self.progress_bar.setFormat("Preparing text...")
            self._append_log(f"Starting synthesis for {len(text)} characters")
            QtWidgets.QApplication.processEvents()

            # Update progress: synthesizing
            self.progress_bar.setValue(30)
            self.progress_bar.setFormat("Synthesizing speech...")
            QtWidgets.QApplication.processEvents()

            # Get speed multiplier from slider
            speed = self.speed_slider.value() / 100.0

            result = self._engine.synthesize_to_file(
                text=text,
                voice_name=self.voice_combo.currentText(),
                output_path=destination,
                speed=speed,
            )

            # Update progress: saving
            self.progress_bar.setValue(90)
            self.progress_bar.setFormat("Saving file...")
            QtWidgets.QApplication.processEvents()

            # Complete
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Complete!")
            self._append_log(f"Wrote {result}")
            self._show_info("Success", f"Saved to {result}")

        except Exception as exc:  # pragma: no cover - GUI level exception
            self._show_error("Generation failed", str(exc))
        finally:
            # Hide progress bar and re-enable button
            self.generate_btn.setEnabled(True)
            # Keep progress bar visible for a moment to show completion
            QtCore.QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))

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
        if self._engine.ffmpeg_path:
            return
        message = (
            "FFmpeg not detected. Install via 'brew install ffmpeg' or set "
            "LK_TTS_FFMPEG_BIN/--ffmpeg-path."
        )
        self._append_log(message)
        # Don't show popup warning - just log it
        # Users can see the message in the log if needed

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
        """Handle multi-speaker dialog generation."""
        if not _DIALOG_TTS_AVAILABLE:
            self._show_error("Feature Unavailable", "Dialog-TTS features are not available.")
            return

        try:
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

            # Show progress
            self.dialog_progress_bar.setVisible(True)
            self.dialog_progress_bar.setRange(0, 100)
            self.dialog_progress_bar.setValue(0)
            self.dialog_progress_bar.setFormat("Preparing...")
            self.dialog_generate_btn.setEnabled(False)
            self._dialog_log("Starting dialog synthesis...")
            QtWidgets.QApplication.processEvents()

            # Create speaker configs
            self.dialog_progress_bar.setValue(10)
            self.dialog_progress_bar.setFormat("Configuring speakers...")
            self._dialog_log("Configuring speakers...")
            QtWidgets.QApplication.processEvents()

            speaker_map = {}

            # Speaker A config
            config_a_dict = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_a_voice.currentText(),
                'rate_wpm': self.speaker_a_rate.value(),
                'gain_db': 0.0,
                'pan': self.speaker_a_pan.value(),
                'aliases': []
            }
            speaker_map['A'] = SpeakerConfig(config_a_dict, engine='edge')

            # Speaker B config
            config_b_dict = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_b_voice.currentText(),
                'rate_wpm': self.speaker_b_rate.value(),
                'gain_db': 0.0,
                'pan': self.speaker_b_pan.value(),
                'aliases': []
            }
            speaker_map['B'] = SpeakerConfig(config_b_dict, engine='edge')

            # Apply custom speaker names if provided
            custom_names = []
            if self.speaker_a_name.text().strip():
                custom_names.append(self.speaker_a_name.text().strip())
            if self.speaker_b_name.text().strip():
                custom_names.append(self.speaker_b_name.text().strip())

            if custom_names:
                speaker_map = apply_speaker_name_mapping(speaker_map, custom_names)
                self._dialog_log(f"Speaker names: {list(speaker_map.keys())}")

            # Initialize engine
            self.dialog_progress_bar.setValue(25)
            self.dialog_progress_bar.setFormat("Initializing TTS engine...")
            self._dialog_log("Initializing TTS engine...")
            QtWidgets.QApplication.processEvents()

            engine = DialogTTSEngine(
                engine='edge',  # Use Edge TTS for natural Korean speech
                sample_rate=int(self.dialog_sr_combo.currentText()),
                stereo=self.dialog_stereo_check.isChecked()
            )

            # Save script to temp file
            self.dialog_progress_bar.setValue(35)
            self.dialog_progress_bar.setFormat("Preparing script...")
            QtWidgets.QApplication.processEvents()

            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(script)
                script_path = Path(f.name)

            try:
                # Synthesize
                self.dialog_progress_bar.setValue(40)
                self.dialog_progress_bar.setFormat("Synthesizing dialog... (this may take a while)")
                self._dialog_log("Synthesizing dialog...")
                QtWidgets.QApplication.processEvents()

                engine.synthesize_dialog(
                    script_path=script_path,
                    speaker_map=speaker_map,
                    output_path=output_path,
                    gap_ms=self.dialog_gap_spin.value(),
                    xfade_ms=20,
                    breath_ms=80,
                    normalize_dbfs=-1.0
                )

                self.dialog_progress_bar.setValue(95)
                self.dialog_progress_bar.setFormat("Finalizing...")
                QtWidgets.QApplication.processEvents()

                self._dialog_log(f"✓ Success! Saved to: {output_path}")
                self.dialog_progress_bar.setValue(100)
                self.dialog_progress_bar.setFormat("Complete!")

                # Show success dialog
                self._show_info("Success", f"Dialog audio generated successfully!\n\nSaved to:\n{output_path}")

            finally:
                # Clean up temp file
                script_path.unlink(missing_ok=True)

        except Exception as exc:
            self._dialog_log(f"✗ Error: {exc}")
            self._show_error("Generation failed", str(exc))

        finally:
            # Re-enable UI
            self.dialog_generate_btn.setEnabled(True)
            # Keep progress bar visible for a moment
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
