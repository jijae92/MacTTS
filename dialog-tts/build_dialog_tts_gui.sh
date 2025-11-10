#!/bin/bash
#
# Dialog TTS GUI 빌드 스크립트 (macOS 전용)
#
# 사용법:
#   ./build_dialog_tts_gui.sh
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Dialog TTS GUI 빌드 스크립트${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 시스템 체크
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}⚠️  경고: 이 스크립트는 macOS에서만 실행 가능합니다.${NC}"
    exit 1
fi

# 의존성 체크
echo -e "${YELLOW}의존성 확인 중...${NC}"

MISSING_DEPS=()

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    MISSING_DEPS+=("pyinstaller")
fi

if ! python3 -c "import PySide6" 2>/dev/null; then
    MISSING_DEPS+=("PySide6")
fi

if ! python3 -c "import edge_tts" 2>/dev/null; then
    MISSING_DEPS+=("edge-tts")
fi

if ! python3 -c "import pydub" 2>/dev/null; then
    MISSING_DEPS+=("pydub")
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    MISSING_DEPS+=("PyYAML")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}✗ 다음 패키지가 설치되지 않았습니다:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo -e "${YELLOW}설치 명령:${NC}"
    echo "  pip install ${MISSING_DEPS[*]}"
    exit 1
fi

echo -e "${GREEN}✓ 모든 의존성이 설치되어 있습니다.${NC}"

# ffmpeg 체크
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  ffmpeg가 설치되지 않았습니다.${NC}"
    echo "  brew install ffmpeg"
    echo ""
fi

# 이전 빌드 정리
echo -e "${YELLOW}이전 빌드 정리 중...${NC}"
rm -rf build/dialog_tts_gui dist/DialogTTS.app

# 빌드 실행
echo ""
echo -e "${BLUE}빌드 시작...${NC}"
python3 -m PyInstaller --clean --noconfirm dialog_tts_gui.spec

# 빌드 결과 확인
if [ -f "dist/DialogTTS.app/Contents/MacOS/dialog_tts_gui" ]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ 빌드 성공!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "앱 위치: ${BLUE}dist/DialogTTS.app${NC}"

    # 앱 정보
    APP_SIZE=$(du -sh dist/DialogTTS.app | awk '{print $1}')
    echo -e "앱 크기: ${BLUE}$APP_SIZE${NC}"
    echo ""

    # 실행 방법
    echo -e "${YELLOW}실행 방법:${NC}"
    echo "  open dist/DialogTTS.app"
    echo ""

    # Applications로 복사
    echo -e "${YELLOW}Applications 폴더로 설치:${NC}"
    echo "  cp -R dist/DialogTTS.app /Applications/"
    echo ""

    # 특징 표시
    echo -e "${GREEN}포함된 기능:${NC}"
    echo "  ✓ 멀티 화자 대화 합성"
    echo "  ✓ Microsoft Edge TTS"
    echo "  ✓ 커스텀 화자 이름"
    echo "  ✓ 스테레오 패닝"
    echo "  ✓ 속도 조절"
    echo "  ✓ 지시문 지원"
    echo ""

else
    echo ""
    echo -e "${RED}✗ 빌드 실패${NC}"
    echo ""
    exit 1
fi
