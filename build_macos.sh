#!/bin/bash
#
# MacTTS GUI 빌드 스크립트 (macOS 전용)
#
# 사용법:
#   ./build_macos.sh
#
# 요구사항:
#   - macOS 13+
#   - Python 3.11+
#   - PyInstaller, PySide6, edge-tts 등 설치됨
#

set -e  # 오류 발생 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  MacTTS GUI 빌드 스크립트 (Enhanced Version)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 시스템 체크
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}⚠️  경고: 이 스크립트는 macOS에서만 실행 가능합니다.${NC}"
    echo -e "${YELLOW}현재 시스템: $OSTYPE${NC}"
    exit 1
fi

# Python 버전 체크
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python 버전: $PYTHON_VERSION"

# PyInstaller 체크
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${RED}✗${NC} PyInstaller가 설치되지 않았습니다."
    echo -e "${YELLOW}설치 중...${NC}"
    pip install pyinstaller
fi
echo -e "${GREEN}✓${NC} PyInstaller 설치됨"

# PySide6 체크
if ! python3 -c "import PySide6" 2>/dev/null; then
    echo -e "${RED}✗${NC} PySide6가 설치되지 않았습니다."
    echo -e "${YELLOW}다음 명령으로 설치하세요:${NC}"
    echo "  pip install PySide6"
    exit 1
fi
echo -e "${GREEN}✓${NC} PySide6 설치됨"

# edge-tts 체크
if ! python3 -c "import edge_tts" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  edge-tts가 설치되지 않았습니다. 설치를 권장합니다.${NC}"
    echo "  pip install edge-tts"
fi

# ffmpeg 체크
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}✗${NC} ffmpeg가 설치되지 않았습니다."
    echo -e "${YELLOW}⚠️  경고: ffmpeg 없이 빌드하면 TTS가 작동하지 않습니다!${NC}"
    echo ""
    echo -e "${YELLOW}ffmpeg 설치:${NC}"
    echo "  brew install ffmpeg"
    echo ""
    read -p "계속 진행하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    FFMPEG_PATH=$(which ffmpeg)
    echo -e "${GREEN}✓${NC} ffmpeg 설치됨: ${BLUE}$FFMPEG_PATH${NC}"
    echo -e "${GREEN}  → 앱 번들에 포함됩니다${NC}"
fi

# 이전 빌드 정리
echo ""
echo -e "${YELLOW}이전 빌드 정리 중...${NC}"
rm -rf build/mac_app dist/localkoreantts-gui

# 빌드 실행
echo ""
echo -e "${BLUE}빌드 시작...${NC}"
python3 -m PyInstaller --clean --noconfirm mac_app.spec

# 빌드 결과 확인
if [ -d "dist/localkoreantts-gui/LocalKoreanTTS.app" ]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ 빌드 성공!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "앱 위치: ${BLUE}dist/localkoreantts-gui/LocalKoreanTTS.app${NC}"

    # 앱 정보 표시
    APP_SIZE=$(du -sh dist/localkoreantts-gui/LocalKoreanTTS.app | awk '{print $1}')
    echo -e "앱 크기: ${BLUE}$APP_SIZE${NC}"
    echo ""

    # 실행 방법
    echo -e "${YELLOW}실행 방법:${NC}"
    echo "  1. Finder에서 앱 더블클릭"
    echo "  2. 터미널: open dist/localkoreantts-gui/LocalKoreanTTS.app"
    echo ""

    # Applications로 복사
    echo -e "${YELLOW}Applications 폴더로 설치:${NC}"
    echo "  cp -R dist/localkoreantts-gui/LocalKoreanTTS.app /Applications/"
    echo ""

    # 코드 서명 (선택사항)
    echo -e "${YELLOW}코드 서명 (선택사항):${NC}"
    echo "  codesign --deep --force --sign - dist/localkoreantts-gui/LocalKoreanTTS.app"
    echo ""

    # 특징 표시
    echo -e "${GREEN}포함된 기능:${NC}"
    echo "  ✓ 단일 화자 TTS (속도 조절 지원)"
    echo "  ✓ 멀티 화자 대화 합성"
    echo "  ✓ Microsoft Edge TTS (10개 한국어 보이스)"
    echo "  ✓ 스테레오 패닝"
    echo "  ✓ 지시문 지원 ([silence=400] 등)"
    echo "  ✓ 다크모드 자동 감지"
    echo "  ✓ 백그라운드 처리 (UI 프리징 없음)"
    if command -v ffmpeg &> /dev/null; then
        echo "  ✓ FFmpeg 번들 포함 (독립 실행 가능)"
    else
        echo "  ⚠️ FFmpeg 미포함 (시스템 설치 필요)"
    fi
    echo ""

else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ 빌드 실패${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "build/mac_app 디렉토리의 로그를 확인하세요."
    exit 1
fi
