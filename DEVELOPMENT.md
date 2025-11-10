# Development Notes

- **Environment**: Run `./mac_bootstrap.sh` (see README “macOS” step 1) to install Python 3.11+, ffmpeg, PySide6, and sounddevice inside `.venv`.
- **Sample model**: `python scripts/setup_test_model.py` populates `LK_TTS_MODEL_PATH` with the Coqui dummy bundle.
- **CLI**: `python -m localkoreantts.cli --help` (or `localkoreantts --help`) shows options; outputs `.wav` and `.meta.json`.
- **GUI**: `localkoreantts-gui` launches the PySide6 interface. For offscreen/headless tests use `QT_QPA_PLATFORM=offscreen`.
- **Tests**: `coverage run -m pytest && coverage report --fail-under=95`.
- **Packaging**: `python -m PyInstaller app_macos.spec` → `dist/localkoreantts-gui.app`. Codesign/notarization commands live in README “macOS packaging”.
