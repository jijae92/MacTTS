"""
Podcast Duet GUI - Main Application

Two-speaker podcast synthesis with timeline view and speaker settings.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional, Dict

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt

from .parser_rules import ScriptParser, TimelineEvent
from .timeline_model import TimelineModel, SynthesisStatus
from .engine_bridge import get_bridge, Voice
from .audio_pipeline import AudioPipeline, SpeakerSettings, check_ffmpeg_available


class PodcastDuetWindow(QtWidgets.QMainWindow):
    """Main window for podcast synthesis."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎙️ Podcast Duet - Two-Speaker TTS")
        self.setMinimumSize(1200, 800)

        # State
        self.current_script_path: Optional[Path] = None
        self.parser = ScriptParser()
        self.bridge = get_bridge()
        self.pipeline = AudioPipeline()

        # Speaker voice assignments
        self.speaker_voices: Dict[str, str] = {}  # speaker -> voice_name
        self.speaker_settings: Dict[str, SpeakerSettings] = {}

        # Setup UI
        self._setup_ui()
        self._setup_menu()

        # Check ffmpeg
        if not check_ffmpeg_available():
            QtWidgets.QMessageBox.warning(
                self,
                "ffmpeg Not Found",
                "ffmpeg is not installed or not in PATH.\n\n"
                "Please install ffmpeg:\n"
                "- macOS: brew install ffmpeg\n"
                "- Windows: Download from ffmpeg.org\n\n"
                "Audio processing will not work without ffmpeg."
            )

    def _setup_ui(self):
        """Setup main UI layout."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        # Main horizontal split
        main_layout = QtWidgets.QHBoxLayout(central)

        # Left: Script editor (60%)
        left_widget = self._create_script_editor()

        # Right: Timeline + Speaker settings (40%)
        right_widget = self._create_right_panel()

        # Splitter
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        main_layout.addWidget(splitter)

        # Bottom: Log panel
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)

        # Add to layout (TODO: proper dock widget)
        # For now, just add log at bottom

        self._log("✓ Podcast Duet GUI initialized")

    def _create_script_editor(self) -> QtWidgets.QWidget:
        """Create left panel with script editor."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()

        open_btn = QtWidgets.QPushButton("📂 Open Script")
        open_btn.clicked.connect(self._open_script)
        toolbar.addWidget(open_btn)

        save_btn = QtWidgets.QPushButton("💾 Save Script")
        save_btn.clicked.connect(self._save_script)
        toolbar.addWidget(save_btn)

        parse_btn = QtWidgets.QPushButton("⚙️ Parse")
        parse_btn.clicked.connect(self._parse_script)
        toolbar.addWidget(parse_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Script text editor
        self.script_edit = QtWidgets.QPlainTextEdit()
        self.script_edit.setPlaceholderText(
            "Enter your podcast script here:\n\n"
            "A: 안녕하세요, 오늘은 좋은 날이에요.\n"
            "B: 네, 맞아요. 날씨가 정말 좋네요.\n"
            "[silence=1s]\n"
            "A: 그래서 저는 산책을 하려고 합니다.\n"
            "B: 좋은 생각이에요!\n\n"
            "Use A:, B: for speakers\n"
            "Use [silence=1s] or [silence=1000ms] for pauses\n"
            "Directives are NEVER read aloud - only processed as audio effects"
        )
        self.script_edit.setFont(QtGui.QFont("Consolas", 11))
        layout.addWidget(self.script_edit)

        return widget

    def _create_right_panel(self) -> QtWidgets.QWidget:
        """Create right panel with timeline and settings."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Timeline view
        timeline_group = QtWidgets.QGroupBox("📋 Timeline")
        timeline_layout = QtWidgets.QVBoxLayout(timeline_group)

        self.timeline_model = TimelineModel()
        self.timeline_view = QtWidgets.QTableView()
        self.timeline_view.setModel(self.timeline_model)
        self.timeline_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.timeline_view.horizontalHeader().setStretchLastSection(True)
        timeline_layout.addWidget(self.timeline_view)

        layout.addWidget(timeline_group, stretch=50)

        # Speaker settings
        speaker_group = self._create_speaker_settings()
        layout.addWidget(speaker_group, stretch=50)

        return widget

    def _create_speaker_settings(self) -> QtWidgets.QWidget:
        """Create speaker configuration panel."""
        group = QtWidgets.QGroupBox("🎤 Speaker Settings")
        layout = QtWidgets.QVBoxLayout(group)

        # Refresh voices button
        refresh_btn = QtWidgets.QPushButton("🔄 Load Voices from MacTTS")
        refresh_btn.clicked.connect(self._load_voices)
        layout.addWidget(refresh_btn)

        # Speaker A
        layout.addWidget(QtWidgets.QLabel("Speaker A:"))
        self.speaker_a_voice = QtWidgets.QComboBox()
        layout.addWidget(self.speaker_a_voice)

        # Speaker B
        layout.addWidget(QtWidgets.QLabel("Speaker B:"))
        self.speaker_b_voice = QtWidgets.QComboBox()
        layout.addWidget(self.speaker_b_voice)

        layout.addStretch()

        # Synthesize button
        synth_btn = QtWidgets.QPushButton("🎵 Synthesize Podcast")
        synth_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-size: 12pt; padding: 10px; font-weight: bold; }"
        )
        synth_btn.clicked.connect(self._synthesize_podcast)
        layout.addWidget(synth_btn)

        return group

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = file_menu.addAction("Open Script...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_script)

        save_action = file_menu.addAction("Save Script...")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_script)

        file_menu.addSeparator()

        quit_action = file_menu.addAction("Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        parse_action = edit_menu.addAction("Parse Script")
        parse_action.setShortcut("Ctrl+P")
        parse_action.triggered.connect(self._parse_script)

    def _log(self, message: str):
        """Add message to log."""
        if hasattr(self, 'log_text'):
            self.log_text.appendPlainText(message)
        print(message)

    def _open_script(self):
        """Open script file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Script",
            str(Path.home()),
            "Text Files (*.txt);;All Files (*)"
        )

        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.script_edit.setPlainText(content)
                self.current_script_path = Path(path)
                self._log(f"✓ Loaded: {path}")

            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to open file:\n{e}"
                )

    def _save_script(self):
        """Save script file."""
        if not self.current_script_path:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Script",
                str(Path.home() / "podcast_script.txt"),
                "Text Files (*.txt)"
            )
            if not path:
                return
            self.current_script_path = Path(path)

        try:
            content = self.script_edit.toPlainText()
            with open(self.current_script_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._log(f"✓ Saved: {self.current_script_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to save file:\n{e}"
            )

    def _parse_script(self):
        """Parse the current script."""
        script_text = self.script_edit.toPlainText()

        if not script_text.strip():
            QtWidgets.QMessageBox.warning(
                self,
                "Empty Script",
                "Please enter some script text first."
            )
            return

        try:
            events = self.parser.parse(script_text)
            self.timeline_model.set_events(events)

            speakers = self.parser.get_speakers()
            self._log(f"✓ Parsed {len(events)} events, {len(speakers)} speakers: {', '.join(speakers)}")

            # Auto-populate voice dropdowns if speakers found
            if 'A' in speakers or 'B' in speakers:
                self._log("Speakers A/B detected")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Parse Error",
                f"Failed to parse script:\n{e}"
            )

    def _load_voices(self):
        """Load available voices from MacTTS."""
        try:
            voices = self.bridge.get_voices()

            self.speaker_a_voice.clear()
            self.speaker_b_voice.clear()

            for voice in voices:
                self.speaker_a_voice.addItem(str(voice), voice.name)
                self.speaker_b_voice.addItem(str(voice), voice.name)

            # Set defaults
            if len(voices) >= 2:
                self.speaker_a_voice.setCurrentIndex(0)
                self.speaker_b_voice.setCurrentIndex(1)

            self._log(f"✓ Loaded {len(voices)} voices from MacTTS")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to load voices:\n{e}"
            )

    def _synthesize_podcast(self):
        """Start podcast synthesis."""
        events = self.timeline_model.events

        if not events:
            QtWidgets.QMessageBox.warning(
                self,
                "No Events",
                "Please parse the script first."
            )
            return

        # Get output path
        output_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Podcast Audio",
            str(Path.home() / "podcast.wav"),
            "WAV Audio (*.wav);;MP3 Audio (*.mp3)"
        )

        if not output_path:
            return

        self._log(f"🎵 Starting synthesis to: {output_path}")

        # TODO: Implement actual synthesis in background thread
        QtWidgets.QMessageBox.information(
            self,
            "Not Implemented",
            "Podcast synthesis is not yet fully implemented.\n\n"
            "This is a working prototype showing the UI structure.\n"
            "The synthesis engine integration is the next step."
        )


def main():
    """Run the application."""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Podcast Duet")
    app.setOrganizationName("MacTTS")

    window = PodcastDuetWindow()
    window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())

