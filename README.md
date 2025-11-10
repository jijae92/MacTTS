# LocalKoreanTTS

LocalKoreanTTS is a cross-platform toolkit that targets feature parity between the
original Windows build and a modern macOS workflow. It ships both a CLI and a PySide6
GUI, plus the plumbing required to package a `.app` bundle with PyInstaller. See
`ARCHITECTURE.md` for an entry-point overview.

## Features
- **High-quality Korean TTS** powered by Microsoft Edge TTS with 10 natural voices
- **Multiple TTS engines** with automatic fallback (edge-tts → gTTS → Coqui TTS)
- **5 voice profiles** including standard and professional male/female voices
- Shared engine leveraged by CLI + GUI launchers
- macOS aware path handling that honors XDG defaults and LK\_TTS\_\* overrides
- Bootstrap script for macOS developers (installs PortAudio, ffmpeg, Python deps)
- PyInstaller spec tuned for generating a signed/notarized-ready `.app`

## Project layout
```
.
├── pyproject.toml            # Project metadata + dependencies
├── requirements.txt          # Editable install with dev/mac extras
├── scripts/mac_bootstrap.sh  # macOS setup helper
├── LocalKoreanTTS-mac.spec   # PyInstaller spec for .app builds
├── src/localkoreantts        # Package source (engine, CLI, GUI)
└── tests                     # pytest suite with CLI/GUI/audio mocks
```

## Prerequisites
1. macOS 13+ with Xcode command line tools
2. Homebrew for installing `ffmpeg` + `portaudio` (required by sounddevice)
3. Python 3.11 (recommended) managed via `pyenv` or the system interpreter

## Installation
```bash
git clone https://github.com/your-org/LocalKoreanTTS.git
cd LocalKoreanTTS
./scripts/mac_bootstrap.sh        # sets up venv + dependencies
source .venv/bin/activate
# or, when skipping the bootstrapper:
pip install .[gui]                # ensures PySide6 for the GUI launcher
```

The bootstrap script installs the editable project with `dev` + `mac` extras so the CLI,
GUI, and test suite all run on macOS without additional steps.

## macOS

### 1. Bootstrap the environment
```bash
./mac_bootstrap.sh
source .venv/bin/activate
```
The script installs/updates Python 3.11+, ffmpeg, PortAudio, and the editable package with GUI/test extras.
If PySide6 fails to import later, run `QT_DEBUG_PLUGINS=1 python check_pyside.py` for detailed
plugin logs (the Cocoa plugin must be present at Qt’s `platforms/` directory).

### 2. Install the sample model
```bash
python scripts/setup_test_model.py
```
This places the Coqui dummy Tacotron2 DDC bundle under `~/.local/share/localkoreantts/model/coqui-tts-tacotron2-ddc`
so both CLI and GUI have something to load.

### 3. Run CLI & GUI
```bash
# CLI example (metadata written beside the WAV)
mkdir -p artifacts
LK_TTS_MODEL_PATH="$HOME/.local/share/localkoreantts/model" \
python -m localkoreantts.cli --in sample/sample.txt --out artifacts/sample_out.wav --lang ko-KR --speed 1.0 --skip-play
ls -l artifacts/sample_out.wav artifacts/sample_out.meta.json

# GUI launcher
localkoreantts-gui
```
Use `--describe` to inspect resolved paths, and pass `--skip-play` when running in environments without CoreAudio access.

### 4. Troubleshooting (macOS)
- **ffmpeg not found**: `brew install ffmpeg`, set `LK_TTS_FFMPEG_BIN`, or pass `--ffmpeg-path /path/to/ffmpeg`.
- **Audio permission prompts**: grant microphone/output access via *System Settings → Privacy & Security → Microphone/Sound*.
- **Playback failures**: rerun without `--play`/disable “Play result” in GUI; confirm another app can play audio.  
  If `pip install sounddevice` fails to ship PortAudio on your host, install it via
  Homebrew (`brew install portaudio`) or MacPorts, then reinstall `sounddevice`.
- **PySide6 plugin errors**: set `QT_DEBUG_PLUGINS=1` and run `python check_pyside.py` to
  confirm the `libqcocoa.dylib` plugin exists. Reinstall PySide6 if missing.
- **Model missing**: rerun `python scripts/setup_test_model.py` or point `LK_TTS_MODEL_PATH` at your own weights.

### 5. Package the GUI
```bash
python -m PyInstaller app_macos.spec
open dist/localkoreantts-gui.app
```
Optionally sign/notarize:
```bash
codesign --deep --force --sign "Developer ID Application: Example" dist/localkoreantts-gui.app
xcrun notarytool submit dist/localkoreantts-gui.zip --wait
```
The bundle keeps LK\_TTS\_\* directories external so users can drop in new voices without rebuilding.

## CLI usage
```bash
# Simple text-to-speech
localkoreantts --text "안녕하세요" --output ~/Desktop/sample.wav

# Use different voices
localkoreantts --text "전문적인 남성 음성입니다" --voice professional-male --output output.wav
localkoreantts --text "표준 여성 음성입니다" --voice standard-female --output output.wav

# List all available voices
localkoreantts --list-voices
# Available voices:
#   - standard-female (ko-KR, 24000 Hz) [SunHiNeural]
#   - standard-male (ko-KR, 24000 Hz) [InJoonNeural]
#   - lite (ko-KR, 16000 Hz) [JiMinNeural]
#   - professional-female (ko-KR, 24000 Hz) [SeoHyeonNeural]
#   - professional-male (ko-KR, 24000 Hz) [HyunsuNeural]

# From file and play audio
localkoreantts --input-file script.txt --voice professional-female --play

# Show system information
localkoreantts --describe

# macOS quick run with sample text + metadata output
mkdir -p artifacts
python -m localkoreantts.cli --in sample/sample.txt --out artifacts/sample_out.wav --lang ko-KR --speed 1.0
ls -l artifacts/sample_out.wav artifacts/sample_out.meta.json
```

- **Default output location**: `~/Downloads/latest.wav` (easy to find!)
- Model data stored in `~/.local/share/localkoreantts/model`
- Cache stored in `~/.cache/localkoreantts`
- `LK_TTS_MODEL_PATH`, `LK_TTS_CACHE_DIR`, and `LK_TTS_FFMPEG_BIN` override the defaults
- `LK_TTS_SAMPLE_RATE` overrides the detected playback sample rate when using `--play`
- `--ffmpeg-path` accepts a manual binary path when bundling or debugging
- Each synthesis also produces `<output>.meta.json` describing the request
- If your CoreAudio device blocks playback, re-run without `--play` (files are always written)

## GUI usage (PySide6)
```bash
localkoreantts-gui
```
The GUI mirrors CLI features: set text, select a preset voice, pick an output file,
and inspect the runtime environment. It runs headlessly under CI thanks to mocked
audio + PySide6 test harnesses.

## macOS packaging

### Quick Build (Recommended)
```bash
# Build the app
source .venv/bin/activate
python -m PyInstaller --clean --noconfirm mac_app.spec

# Install to Applications folder
cp -R dist/LocalKoreanTTS.app /Applications/

# Launch from Applications or Spotlight
open -a LocalKoreanTTS
```

The app will be available at `/Applications/LocalKoreanTTS.app` and can be launched like any other macOS app!

### Detailed Build Steps
1. `python -m PyInstaller --distpath dist --workpath build/mac_app mac_app.spec` – builds a windowed bundle with edge-tts, gTTS, and PySide6. The output is at `dist/LocalKoreanTTS.app`.
2. Launch locally for a smoke test: `open dist/LocalKoreanTTS.app`
3. Copy to Applications: `cp -R dist/LocalKoreanTTS.app /Applications/`
4. (Optional) Sign for distribution:
   `codesign --deep --force --options runtime --sign "Developer ID Application: Example" /Applications/LocalKoreanTTS.app`
5. (Optional) Notarize with Apple:
   ```bash
   ditto -c -k --keepParent /Applications/LocalKoreanTTS.app dist/LocalKoreanTTS.zip
   xcrun notarytool submit dist/LocalKoreanTTS.zip --apple-id you@example.com --team-id ABCDE12345 --keychain-profile notarization-profile --wait
   ```
6. (Optional) Staple the ticket:
   `xcrun stapler staple /Applications/LocalKoreanTTS.app`

**Note**: The app includes edge-tts and gTTS for high-quality Korean TTS. It does NOT include the large Coqui TTS models to keep the app size reasonable (~673MB).

## Testing
```bash
pytest
pytest --cov=localkoreantts
# or enforce coverage gates locally
coverage run -m pytest && coverage report --fail-under=95
```

Tests provide headless coverage for the GUI via PySide6 and mock the audio backend so
audio hardware is never accessed during CI runs.

## Test Model Installation
Need a quick sample voice for demos? Download the Coqui TTS dummy Tacotron2 DDC fixtures
into the model directory:

```bash
python scripts/setup_test_model.py
```

- Files land under `~/.local/share/localkoreantts/model/coqui-tts-tacotron2-ddc`.
- Re-run with `--force` to refresh, or override the source archive via
  `LK_TTS_TEST_MODEL_URL`.
- Model courtesy of [Coqui TTS (Tacotron2 DDC)](https://github.com/coqui-ai/TTS#license)
  (MPL 2.0). Review the upstream LICENSE before redistribution.

## Troubleshooting
- **ffmpeg not found**: install via `brew install ffmpeg` or pass `--ffmpeg-path`.
- **sounddevice errors**: ensure `brew install portaudio` and re-run `mac_bootstrap.sh`.
- **Permission issues when packaging**: remove the quarantine attribute using  
  `xattr -dr com.apple.quarantine dist/LocalKoreanTTS.app`.
