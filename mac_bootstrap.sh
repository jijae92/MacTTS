#!/usr/bin/env bash
set -euo pipefail

echo "==> LocalKoreanTTS macOS bootstrap"

ensure_python() {
  local requested_bin=${PYTHON_BIN:-}
  local candidates=()
  if [ -n "$requested_bin" ]; then
    candidates+=("$requested_bin")
  fi
  candidates+=("python3.12" "python3.11" "python3")

  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
        PYTHON_BIN="$candidate"
        return 0
      fi
    fi
  done

  if command -v brew >/dev/null 2>&1; then
    echo "==> Installing python@3.11 via Homebrew" >&2
    brew install python@3.11 >&2
    local brew_bin
    brew_bin="$(brew --prefix)/opt/python@3.11/bin/python3.11"
    if [ -x "$brew_bin" ]; then
      PYTHON_BIN="$brew_bin"
      return 0
    fi
  fi

  return 1
}

ensure_python || {
  echo "❌ Unable to locate a Python 3.11+ interpreter. Install one (e.g., 'brew install python@3.11') and set PYTHON_BIN." >&2
  exit 1
}

PY_VERSION="$("$PYTHON_BIN" --version 2>&1)"
echo "==> Using Python interpreter: $PYTHON_BIN ($PY_VERSION)"

if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)"
  "$PYTHON_BIN" -m venv .venv
else
  echo "==> Reusing existing virtual environment (.venv)"
fi

source .venv/bin/activate

echo "==> Upgrading pip"
python -m pip install --upgrade pip

if [ -f requirements.txt ]; then
  echo "==> Installing project requirements"
  python -m pip install -r requirements.txt
else
  echo "⚠️  requirements.txt not found; skipping"
fi

echo "==> Installing PySide6 (Qt)"
python -m pip install PySide6

echo "==> Installing sounddevice (PortAudio)"
python -m pip install sounddevice

if command -v brew >/dev/null 2>&1; then
  if brew list ffmpeg >/dev/null 2>&1; then
    echo "==> Homebrew ffmpeg already installed"
  else
    echo "==> Installing ffmpeg via Homebrew"
    brew install ffmpeg
  fi
else
  echo "⚠️  Homebrew not found. Install from https://brew.sh to manage ffmpeg, then rerun this script."
fi

FFMPEG_PATH="$(command -v ffmpeg || true)"

python <<'PY'
import importlib
summary = []
for package in ("PySide6", "sounddevice"):
    try:
        module = importlib.import_module(package)
        version = getattr(module, "__version__", "unknown")
        summary.append(f"{package}: OK (version {version})")
    except Exception as exc:
        summary.append(f"{package}: FAILED ({exc})")
print("\n".join(summary))
PY

if [ -n "$FFMPEG_PATH" ]; then
  echo "ffmpeg binary: $FFMPEG_PATH"
else
  echo "ffmpeg binary: NOT FOUND"
fi

echo "==> Bootstrap complete. Activate via 'source .venv/bin/activate'."
