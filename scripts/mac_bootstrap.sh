#!/usr/bin/env bash
set -euo pipefail

echo ">> LocalKoreanTTS macOS bootstrapper"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install from https://brew.sh first." >&2
  exit 1
fi

echo ">> Ensuring Homebrew dependencies"
brew list portaudio >/dev/null 2>&1 || brew install portaudio
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg

PYTHON_BIN=${PYTHON_BIN:-python3}

if [ ! -d ".venv" ]; then
  echo ">> Creating virtual environment (.venv)"
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -e .[dev,mac]

echo ">> Bootstrap complete. Activate via 'source .venv/bin/activate'."
