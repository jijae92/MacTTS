# MacTTS 빌드 가이드

MacTTS 프로젝트를 macOS 애플리케이션으로 빌드하는 방법을 설명합니다.

## 📋 목차

- [시스템 요구사항](#시스템-요구사항)
- [빠른 시작](#빠른-시작)
- [상세 빌드 절차](#상세-빌드-절차)
- [빌드 산출물](#빌드-산출물)
- [트러블슈팅](#트러블슈팅)

## 시스템 요구사항

### 필수

- **macOS 13.0+** (Ventura 이상)
- **Python 3.11+**
- **Xcode Command Line Tools**
  ```bash
  xcode-select --install
  ```
- **Homebrew** (권장)
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

### 의존성

```bash
# ffmpeg (필수)
brew install ffmpeg

# Python 패키지
pip install pyinstaller PySide6 edge-tts pydub PyYAML pyloudnorm
```

## 빠른 시작

### 1. 리포지토리 클론 및 의존성 설치

```bash
# 클론
git clone https://github.com/your-org/MacTTS.git
cd MacTTS

# 의존성 설치 (bootstrap 스크립트 사용)
./mac_bootstrap.sh
source .venv/bin/activate
```

### 2. 빌드 실행

```bash
# 빌드 스크립트 실행
chmod +x build_macos.sh
./build_macos.sh

# 또는 수동 빌드
python -m PyInstaller --clean --noconfirm mac_app.spec
```

빌드 완료 후:
- 앱 위치: `dist/localkoreantts-gui/LocalKoreanTTS.app`
- 앱 크기: 약 150-200 MB

### 3. 앱 설치

```bash
# Applications 폴더에 복사
cp -R dist/localkoreantts-gui/LocalKoreanTTS.app /Applications/

# Spotlight에서 실행
# "LocalKoreanTTS" 검색
```

## 상세 빌드 절차

### 1. 환경 준비

```bash
# 1. 프로젝트 디렉토리로 이동
cd MacTTS

# 2. 가상 환경 생성 (권장)
python3 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### 2. PyInstaller Spec 파일 이해

`mac_app.spec` 파일에는 다음과 같은 설정이 포함되어 있습니다:

```python
# 주요 설정
- Entry Point: gui_entry.py
- App Name: LocalKoreanTTS.app
- Icon: resources/app_icon.icns
- Hidden Imports: PySide6, edge-tts, gtts, pydub
- Excludes: PyQt5, PyQt6, TTS, torch (크기 최적화)
```

### 3. 빌드 실행

```bash
# 이전 빌드 정리
rm -rf build/mac_app dist/localkoreantts-gui

# 빌드 실행 (권장)
python -m PyInstaller --clean --noconfirm mac_app.spec

# 또는 빌드 스크립트 사용
./build_macos.sh
```

### 4. 빌드 확인

```bash
# 앱 파일 확인
ls -lh dist/localkoreantts-gui/LocalKoreanTTS.app/Contents/MacOS/gui_entry

# 앱 실행 테스트
open dist/localkoreantts-gui/LocalKoreanTTS.app
```

## 빌드 산출물

### LocalKoreanTTS.app

```
dist/localkoreantts-gui/LocalKoreanTTS.app/
├── Contents/
│   ├── MacOS/
│   │   └── gui_entry              # 실행 파일
│   ├── Resources/
│   │   ├── app_icon.icns          # 앱 아이콘
│   │   ├── docs/README.md         # 문서
│   │   └── sample/sample.txt      # 샘플
│   ├── Frameworks/                # Python, PySide6 등
│   └── Info.plist                 # 앱 메타데이터
```

**포함된 기능:**
- ✅ 단일 화자 TTS (속도 조절)
- ✅ 멀티 화자 대화 합성
- ✅ Microsoft Edge TTS (10개 한국어 보이스)
- ✅ 음성 프로필 선택
- ✅ 출력 파일 선택
- ✅ 진행률 표시
- ✅ 스테레오 패닝
- ✅ 화자별 속도 조절

**앱 크기:** 약 150-200 MB

## 고급 설정

### 1. 코드 서명 (배포용)

```bash
# 개발자 인증서로 서명
codesign --deep --force --sign "Developer ID Application: Your Name" \
  dist/localkoreantts-gui/LocalKoreanTTS.app

# 서명 확인
codesign --verify --verbose=2 dist/localkoreantts-gui/LocalKoreanTTS.app
```

### 2. 공증 (Notarization)

```bash
# DMG 생성
hdiutil create -volname "LocalKoreanTTS" -srcfolder dist/localkoreantts-gui/LocalKoreanTTS.app -ov -format UDZO LocalKoreanTTS.dmg

# 공증 제출
xcrun notarytool submit LocalKoreanTTS.dmg \
  --apple-id your@email.com \
  --team-id YOUR_TEAM_ID \
  --password app-specific-password \
  --wait

# 공증 확인 및 stapling
xcrun stapler staple dist/localkoreantts-gui/LocalKoreanTTS.app
```

### 3. DMG 배포 패키지 생성

```bash
# create-dmg 설치
brew install create-dmg

# DMG 생성
create-dmg \
  --volname "LocalKoreanTTS" \
  --volicon "resources/app_icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "LocalKoreanTTS.app" 200 190 \
  --hide-extension "LocalKoreanTTS.app" \
  --app-drop-link 600 185 \
  "LocalKoreanTTS-Installer.dmg" \
  "dist/localkoreantts-gui/"
```

## 빌드 최적화

### 1. 크기 줄이기

```python
# mac_app.spec에서 불필요한 모듈 제외
excludes=[
    "PyQt5", "PyQt6", "PySide2",  # 다른 Qt 바인딩
    "TTS", "torch", "transformers",  # 대용량 ML 라이브러리
    "matplotlib", "scipy",  # 사용하지 않는 과학 라이브러리
]
```

### 2. 빌드 속도 높이기

```bash
# UPX로 압축 (선택사항)
brew install upx
python -m PyInstaller --upx-dir=/opt/homebrew/bin mac_app.spec

# 병렬 빌드
python -m PyInstaller --jobs 4 mac_app.spec
```

### 3. 디버그 빌드

```bash
# 디버그 모드 빌드 (콘솔 출력 확인)
python -m PyInstaller --debug all mac_app.spec

# 로그 확인
open dist/localkoreantts-gui/LocalKoreanTTS.app
# 터미널에서 실행하면 디버그 출력 확인 가능
```

## 트러블슈팅

### 문제 1: PySide6 플러그인 오류

```
This application failed to start because no Qt platform plugin could be initialized
```

**해결:**
```bash
# QT_DEBUG_PLUGINS 환경변수 설정하고 재빌드
export QT_DEBUG_PLUGINS=1
python -m PyInstaller --clean mac_app.spec

# 또는 spec 파일에 명시적으로 플러그인 추가
hiddenimports=[
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]
```

### 문제 2: ffmpeg 경로 문제

```
FileNotFoundError: ffmpeg not found
```

**해결:**
```bash
# ffmpeg를 앱 번들에 포함
# mac_app.spec에 추가:
import shutil
ffmpeg_path = shutil.which('ffmpeg')
binaries = [(ffmpeg_path, '.')] if ffmpeg_path else []
```

### 문제 3: edge-tts 임포트 오류

```
ModuleNotFoundError: No module named 'edge_tts'
```

**해결:**
```bash
# spec 파일의 hiddenimports에 추가
hiddenimports=[
    'edge_tts',
    'aiohttp',
    'certifi',
]
```

### 문제 4: 앱 실행 시 권한 오류

```
"LocalKoreanTTS.app" is damaged and can't be opened
```

**해결:**
```bash
# Gatekeeper 속성 제거
xattr -cr dist/localkoreantts-gui/LocalKoreanTTS.app

# 또는 시스템 설정 → 보안 및 개인정보보호에서 허용
```

### 문제 5: dialog-tts 모듈 찾을 수 없음

```
ModuleNotFoundError: No module named 'dialog_tts'
```

**해결:**
```python
# mac_app.spec에 dialog-tts 경로 추가
import sys
sys.path.insert(0, 'dialog-tts')

# 또는 hiddenimports에 추가
hiddenimports=[
    'dialog_tts',
    'parser_utils',
    'audio_utils',
]
```

## 빌드 스크립트 사용

```bash
# 실행 권한 부여
chmod +x build_macos.sh

# 빌드 실행
./build_macos.sh

# 성공 시 출력:
# ✓ 빌드 성공!
# 앱 위치: dist/localkoreantts-gui/LocalKoreanTTS.app
```

## CI/CD 자동 빌드

### GitHub Actions 예시

```yaml
name: Build macOS App

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          brew install ffmpeg
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build app
        run: ./build_macos.sh

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: LocalKoreanTTS-macOS
          path: dist/localkoreantts-gui/LocalKoreanTTS.app
```

## Linux 테스트 빌드

macOS가 없는 환경에서 코드 검증을 위해 Linux 실행 파일을 빌드할 수 있습니다.

```bash
# Linux 테스트 빌드 실행
python3 build_linux_test.py
```

**주의사항:**
- 이 빌드는 코드 검증용이며, macOS .app 번들을 생성하지 않습니다
- 생성된 실행 파일은 Linux에서만 작동합니다
- 실제 macOS 앱 배포를 위해서는 macOS에서 빌드해야 합니다

**빌드 결과:**
- 위치: `dist/LocalKoreanTTS-Linux`
- 크기: 약 300MB
- 형식: ELF 64-bit executable

## 추가 리소스

- [PyInstaller 공식 문서](https://pyinstaller.org/)
- [PySide6 문서](https://doc.qt.io/qtforpython/)
- [macOS 앱 번들 구조](https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html)
- [코드 서명 가이드](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

## 문의

빌드 관련 문제가 있으면 GitHub Issues에 보고해주세요:
- [Issues 페이지](https://github.com/your-org/MacTTS/issues)
