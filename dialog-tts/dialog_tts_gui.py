#!/usr/bin/env python3
"""
Dialog TTS GUI - Multi-speaker dialog synthesis interface
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Optional

try:
    from PySide6 import QtCore, QtWidgets
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("Error: PySide6 is required for GUI. Install with: pip install PySide6")
    sys.exit(1)

# Import dialog TTS modules
from dialog_tts import (
    DialogTTSEngine,
    SpeakerConfig,
    apply_speaker_name_mapping,
)

# Configure pydub to find ffmpeg
try:
    from pydub import AudioSegment
    import subprocess
    import os

    # Try to find ffmpeg/ffprobe
    ffmpeg_paths = [
        '/opt/homebrew/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg',
    ]

    ffprobe_paths = [
        '/opt/homebrew/bin/ffprobe',
        '/usr/local/bin/ffprobe',
        '/usr/bin/ffprobe',
    ]

    # Set ffmpeg path
    for path in ffmpeg_paths:
        if Path(path).exists():
            AudioSegment.converter = path
            os.environ['FFMPEG_BINARY'] = path
            print(f"Set ffmpeg to: {path}")
            break

    # Set ffprobe path
    for path in ffprobe_paths:
        if Path(path).exists():
            AudioSegment.ffprobe = path
            os.environ['FFPROBE_BINARY'] = path
            print(f"Set ffprobe to: {path}")
            break

    # Also add common bin directories to PATH
    homebrew_bin = '/opt/homebrew/bin'
    if homebrew_bin not in os.environ.get('PATH', ''):
        os.environ['PATH'] = homebrew_bin + ':' + os.environ.get('PATH', '')

except Exception as e:
    print(f"Warning: Could not configure ffmpeg paths: {e}")


class DialogTTSWindow(QtWidgets.QMainWindow):
    """GUI for Dialog TTS multi-speaker synthesis."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dialog TTS - Multi-Speaker Synthesis")
        self.setMinimumSize(800, 700)

        # State
        self.engine: Optional[DialogTTSEngine] = None

        # Build UI
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # Title
        title = QtWidgets.QLabel("Dialog TTS - Multi-Speaker Synthesis")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; margin: 10px;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(title)

        # Script input
        script_group = QtWidgets.QGroupBox("Dialog Script")
        script_layout = QtWidgets.QVBoxLayout(script_group)

        script_label = QtWidgets.QLabel("Enter your dialog (use A:, B: for speakers):")
        script_layout.addWidget(script_label)

        self.script_text = QtWidgets.QPlainTextEdit()
        self.script_text.setPlaceholderText(
            "A: 안녕하세요. 일정 확인하셨어요?\n"
            "B: 네, 10시에 스탠드업부터 시작해요.\n\n"
            "[silence=400]\n\n"
            "A: 그 다음은 보안 점검 보고서 리뷰죠.\n"
            "B: 맞아요. 성능 테스트도 같이 봐요."
        )
        self.script_text.setMinimumHeight(200)
        script_layout.addWidget(self.script_text)
        main_layout.addWidget(script_group)

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
        self.speaker_a_voice.addItems(["Yuna", "Jinho", "Default"])
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
        self.speaker_b_voice.addItems(["Jinho", "Yuna", "Default"])
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

        main_layout.addWidget(speaker_group)

        # Audio settings
        audio_group = QtWidgets.QGroupBox("Audio Settings")
        audio_layout = QtWidgets.QGridLayout(audio_group)

        self.stereo_check = QtWidgets.QCheckBox("Stereo Output (with panning)")
        self.stereo_check.setChecked(True)
        audio_layout.addWidget(self.stereo_check, 0, 0, 1, 2)

        audio_layout.addWidget(QtWidgets.QLabel("Gap (ms):"), 1, 0)
        self.gap_spin = QtWidgets.QSpinBox()
        self.gap_spin.setRange(0, 2000)
        self.gap_spin.setValue(250)
        audio_layout.addWidget(self.gap_spin, 1, 1)

        audio_layout.addWidget(QtWidgets.QLabel("Sample Rate:"), 1, 2)
        self.sr_combo = QtWidgets.QComboBox()
        self.sr_combo.addItems(["24000", "22050", "16000"])
        audio_layout.addWidget(self.sr_combo, 1, 3)

        main_layout.addWidget(audio_group)

        # Output
        output_group = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QHBoxLayout(output_group)

        output_layout.addWidget(QtWidgets.QLabel("Save to:"))
        self.output_path = QtWidgets.QLineEdit()
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        self.output_path.setText(str(downloads / "dialog.wav"))
        output_layout.addWidget(self.output_path)

        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(browse_btn)

        main_layout.addWidget(output_group)

        # Generate button
        self.generate_btn = QtWidgets.QPushButton("Generate Dialog Audio")
        self.generate_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-size: 14pt; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.generate_btn.clicked.connect(self._generate)
        main_layout.addWidget(self.generate_btn)

        # Progress and log
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        main_layout.addWidget(QtWidgets.QLabel("Log:"))
        main_layout.addWidget(self.log_text)

        self._log("Ready to generate dialog audio")
        self._check_ffmpeg()

    def _log(self, message: str):
        """Add message to log."""
        self.log_text.appendPlainText(message)

    def _check_ffmpeg(self):
        """Check if ffmpeg is available."""
        import shutil

        ffmpeg = shutil.which('ffmpeg')
        ffprobe = shutil.which('ffprobe')

        if not ffmpeg or not ffprobe:
            self._log("⚠️ Warning: ffmpeg not found in PATH")
            self._log("Install with: brew install ffmpeg")
            self._log("Attempting to use common paths...")

            # Try common paths
            tried_paths = []
            for base in ['/opt/homebrew/bin', '/usr/local/bin']:
                ffmpeg_path = Path(base) / 'ffmpeg'
                if ffmpeg_path.exists():
                    self._log(f"✓ Found ffmpeg at: {ffmpeg_path}")
                    return
                tried_paths.append(str(ffmpeg_path))

            self._log(f"✗ ffmpeg not found at: {', '.join(tried_paths)}")
            QtWidgets.QMessageBox.warning(
                self,
                "ffmpeg Not Found",
                "ffmpeg is required for audio processing.\n\n"
                "Please install it:\n"
                "  brew install ffmpeg\n\n"
                "The application may not work correctly without it."
            )
        else:
            self._log(f"✓ ffmpeg found: {ffmpeg}")
            self._log(f"✓ ffprobe found: {ffprobe}")

    def _browse_output(self):
        """Browse for output file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Dialog Audio",
            self.output_path.text(),
            "Audio Files (*.wav *.mp3)"
        )
        if path:
            self.output_path.setText(path)

    def _generate(self):
        """Generate dialog audio."""
        try:
            # Validate inputs
            script = self.script_text.toPlainText().strip()
            if not script:
                QtWidgets.QMessageBox.warning(
                    self, "Error", "Please enter a dialog script"
                )
                return

            output_path = Path(self.output_path.text())
            if not output_path.parent.exists():
                QtWidgets.QMessageBox.warning(
                    self, "Error", f"Output directory does not exist: {output_path.parent}"
                )
                return

            # Disable UI and show progress
            self.generate_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("Preparing...")
            self._log("\n" + "="*50)
            self._log("Starting synthesis...")
            QtWidgets.QApplication.processEvents()

            # Create speaker configs
            self.progress.setValue(10)
            self.progress.setFormat("Configuring speakers...")
            self._log("Configuring speakers...")
            QtWidgets.QApplication.processEvents()
            speaker_map = {}

            # Speaker A
            config_a_dict = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_a_voice.currentText(),
                'rate_wpm': self.speaker_a_rate.value(),
                'gain_db': 0.0,
                'pan': self.speaker_a_pan.value(),
                'aliases': []
            }
            speaker_map['A'] = SpeakerConfig(config_a_dict, engine='edge')

            # Speaker B
            config_b_dict = {
                'voice_hint': 'ko_KR',
                'voice_name': self.speaker_b_voice.currentText(),
                'rate_wpm': self.speaker_b_rate.value(),
                'gain_db': -1.0,
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
                self._log(f"Speaker names: {list(speaker_map.keys())}")

            # Initialize engine
            self.progress.setValue(25)
            self.progress.setFormat("Initializing TTS engine...")
            self._log("Initializing TTS engine...")
            QtWidgets.QApplication.processEvents()

            self.engine = DialogTTSEngine(
                engine='edge',  # Use Edge TTS for natural Korean speech
                sample_rate=int(self.sr_combo.currentText()),
                stereo=self.stereo_check.isChecked()
            )

            # Save script to temp file
            self.progress.setValue(35)
            self.progress.setFormat("Preparing script...")
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
                self.progress.setValue(40)
                self.progress.setFormat("Synthesizing dialog... (this may take a while)")
                self._log("Synthesizing dialog...")
                QtWidgets.QApplication.processEvents()

                self.engine.synthesize_dialog(
                    script_path=script_path,
                    speaker_map=speaker_map,
                    output_path=output_path,
                    gap_ms=self.gap_spin.value(),
                    xfade_ms=20,
                    breath_ms=80,
                    normalize_dbfs=-1.0
                )

                self.progress.setValue(95)
                self.progress.setFormat("Finalizing...")
                QtWidgets.QApplication.processEvents()

                self._log(f"✓ Success! Saved to: {output_path}")

                self.progress.setValue(100)
                self.progress.setFormat("Complete!")

                # Show success dialog
                QtWidgets.QMessageBox.information(
                    self,
                    "Success",
                    f"Dialog audio generated successfully!\n\nSaved to:\n{output_path}"
                )

            finally:
                # Clean up temp file
                script_path.unlink(missing_ok=True)

        except Exception as e:
            self._log(f"✗ Error: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to generate audio:\n\n{str(e)}"
            )

        finally:
            # Re-enable UI
            self.generate_btn.setEnabled(True)
            self.progress.setVisible(False)


def main():
    """Run the GUI application."""
    app = QtWidgets.QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Dialog TTS")
    app.setOrganizationName("Dialog TTS")

    window = DialogTTSWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
