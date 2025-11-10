# LocalKoreanTTS Architecture

This document summarizes the macOS-first layout that mirrors the README “Installation → macOS → CLI/GUI → Packaging” flow.

## High-level tree
```
.
├── src/localkoreantts
│   ├── cli.py          # CLI entry (python -m localkoreantts.cli / console script)
│   ├── gui.py          # PySide6 window + helpers
│   ├── paths.py        # XDG-style path resolution (README “Defaults”)
│   ├── ffmpeg.py       # PATH/env detection (README “Troubleshooting”)
│   ├── audio_io.py     # sounddevice layer (README “CLI usage” notes)
│   ├── models.py       # ensures LK_TTS_MODEL_PATH contents
│   └── __init__.py     # exports engine + config helpers
├── gui_entry.py        # Thin shim for PyInstaller (--console disabled)
├── app_macos.spec      # PyInstaller spec (README “macOS packaging”)
├── mac_bootstrap.sh    # Developer bootstrap (README “macOS” step 1)
├── mac_e2e_test.sh     # Full smoke test (README “macOS” flow)
└── tests/…             # pytest suite (README “Testing”)
```

## Entry points
- **CLI (`localkoreantts` / `python -m localkoreantts.cli`)**  
  Defined in `pyproject.toml [project.scripts]` and implemented by `src/localkoreantts/cli.py`.  
  Produces `.wav` + `.meta.json`, mirrors README’s “CLI usage” + “macOS” examples.  
  Relies on `paths.py`, `ffmpeg.py`, `models.py`, and `audio_io.py`.

- **GUI (`localkoreantts-gui`)**  
  Also registered under `[project.scripts]`, backed by `src/localkoreantts/gui.py`.  
  `gui_entry.py` exists purely for PyInstaller bundling so the app can be launched via Finder (`open dist/localkoreantts-gui.app` per README “macOS packaging”).

## Packaging workflow
1. `./mac_bootstrap.sh` — installs Python 3.11, PySide6, sounddevice, ffmpeg (README “macOS” step 1).
2. `python scripts/setup_test_model.py` — installs sample model (README “macOS” step 2).
3. `python -m PyInstaller app_macos.spec` — builds `.app`, optional `codesign`/`notarytool` commands follow (README “macOS packaging”).

The README sections are referenced directly in `cli.py` and `gui.py` docstrings to keep code and docs synchronized.
