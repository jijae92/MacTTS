"""PySide6 GUI tailored for macOS and cross-platform use.

Referenced by README “macOS → 3. Run CLI & GUI” and “GUI usage”; packaging flow
is detailed under “macOS packaging” and ARCHITECTURE.md.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from .cli import _voice_lines
from .engine import LocalKoreanTTSEngine
from .paths import PathConfig, resolve_path_config

IS_MAC = sys.platform == "darwin"


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
        self._tabs.addTab(self._build_synthesis_tab(), "Synthesis")
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

            result = self._engine.synthesize_to_file(
                text=text,
                voice_name=self.voice_combo.currentText(),
                output_path=destination,
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
