#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
LOG_DIR="${ROOT_DIR}/artifacts"
GUI_LOG="/tmp/localkoreantts_gui.log"

step() { printf "\n=== [STEP] %s ===\n" "$*"; }

# 0) 환경 점검 (선택)
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "python not found"; exit 1;
fi

# 1) bootstrap (맥 의존성+venv+pip 설치)
step "1. ./mac_bootstrap.sh"
bash "${ROOT_DIR}/mac_bootstrap.sh"

# 2) 테스트 모델 설치
step "2. setup_test_model.py"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python scripts/setup_test_model.py

# 3) CLI 스모크 테스트 (skip-play)
step "3. CLI run -> artifacts/sample_out.wav 생성"
mkdir -p "${LOG_DIR}"
LK_TTS_MODEL_PATH="$HOME/.local/share/localkoreantts/model" \
python -m localkoreantts.cli \
  --in sample/sample.txt \
  --out "${LOG_DIR}/sample_out.wav" \
  --lang ko-KR \
  --speed 1.0 \
  --skip-play

test -s "${LOG_DIR}/sample_out.wav" && echo "[OK] wav created: ${LOG_DIR}/sample_out.wav"

# 4) GUI 기동/종료 스모크
step "4. GUI launch/kill (3초 스모크)"
( localkoreantts-gui >"${GUI_LOG}" 2>&1 & GUI_PID=$!; sleep 3; kill "${GUI_PID}" >/dev/null 2>&1 || true )
echo "[OK] GUI launched and terminated. Logs: ${GUI_LOG}"

# 5) PyInstaller 빌드 (.app 번들 생성)
step "5. PyInstaller build"
python -m PyInstaller app_macos.spec

# 6) 앱 열기 (수동 확인)
step "6. open dist/localkoreantts-gui.app"
if [ -d "${ROOT_DIR}/dist/localkoreantts-gui.app" ]; then
  open "${ROOT_DIR}/dist/localkoreantts-gui.app"
  echo "[INFO] If Gatekeeper warns, right-click → Open."
else
  echo "[ERROR] .app not found at dist/localkoreantts-gui.app"
  exit 2
fi

echo -e "\nAll steps completed."
